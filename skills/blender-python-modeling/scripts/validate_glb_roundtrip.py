"""Audit a static, textured GLB against its prepared Blender export collection."""

import argparse
import json
import struct
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage_guard import file_input


CHANNELS = ("Base Color", "Metallic", "Roughness", "Transmission Weight")
GRID = 384
AXIS = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])  # Blender (x,y,z) -> glTF (x,z,-y)


def write(path, report):
    path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def bounds(points):
    if not len(points) or not np.isfinite(points).all():
        raise ValueError("Empty or nonfinite geometry")
    return [points.min(axis=0).tolist(), points.max(axis=0).tolist()]


def close(a, b, atol=1e-5):
    return bool(np.allclose(a, b, atol=atol, rtol=0))


def uv_overlap(triangles):
    """Approximate overlap by sampling texel centers strictly inside each UV triangle."""
    covered = np.zeros((GRID, GRID), dtype=np.uint16)
    for triangle in triangles * GRID:
        lo = np.maximum(np.floor(triangle.min(axis=0)).astype(int), 0)
        hi = np.minimum(np.ceil(triangle.max(axis=0)).astype(int), GRID)
        if np.any(lo >= hi):
            continue
        x = np.arange(lo[0], hi[0])[None, :] + 0.5
        y = np.arange(lo[1], hi[1])[:, None] + 0.5
        a, b, c = triangle
        edges = [(q[0]-p[0])*(y-p[1]) - (q[1]-p[1])*(x-p[0]) for p, q in ((a, b), (b, c), (c, a))]
        positive = (edges[0] > 1e-5) & (edges[1] > 1e-5) & (edges[2] > 1e-5)
        negative = (edges[0] < -1e-5) & (edges[1] < -1e-5) & (edges[2] < -1e-5)
        covered[lo[1]:hi[1], lo[0]:hi[0]] += positive | negative
    used = int(np.count_nonzero(covered))
    return {"grid": GRID, "sampled_texels": used, "overlap_texels": int(np.count_nonzero(covered > 1))}


def uv_record(mesh, points):
    if not mesh.uv_layers:
        return {"layers": 0}, None
    layer = mesh.uv_layers.active
    loops = np.array([list(item.uv) for item in layer.data], dtype=np.float64)
    if not np.isfinite(loops).all():
        raise ValueError(f"Nonfinite UV coordinates in {mesh.name}")
    triangles = loops[np.array([list(t.loops) for t in mesh.loop_triangles])]
    ab, ac = triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    area2 = abs(ab[:, 0]*ac[:, 1] - ab[:, 1]*ac[:, 0])
    report = {"layers": len(mesh.uv_layers), "active_layer": layer.name, "bounds": bounds(loops),
              "degenerate_triangles": int(np.count_nonzero(area2 <= 1e-10)), **uv_overlap(triangles)}
    corners = np.unique(np.column_stack((points[[loop.vertex_index for loop in mesh.loops]], loops)), axis=0)
    return report, corners


def uv_mapping_equal(a, b):
    """Compare position/UV pairs without relying on exported loop or vertex indices."""
    def contains(source, target):
        tree = KDTree(len(target))
        for i, item in enumerate(target):
            tree.insert(item[:3], i)
        tree.balance()
        return all(any(close(item[3:], target[index, 3:], 2e-6)
                       for _, index, _ in tree.find_range(item[:3], 2e-7)) for item in source)

    return a is not None and b is not None and contains(a, b) and contains(b, a)


def image_record(image, cache):
    if image.as_pointer() not in cache:
        width, height = image.size
        if not width or not height:
            raise ValueError(f"Missing image pixels: {image.name}")
        pixels = np.empty(len(image.pixels), dtype=np.float32)
        image.pixels.foreach_get(pixels)
        encoded = np.rint(np.clip(pixels, 0, 1) * 255).astype(np.uint8)
        cache[image.as_pointer()] = {"size": [width, height], "color_space": image.colorspace_settings.name,
                                    "pixel_sha256": sha256(encoded.tobytes()).hexdigest()}
    return cache[image.as_pointer()]


def channel_record(socket, images):
    if not socket.is_linked:
        value = socket.default_value
        return {"constant": list(value) if hasattr(value, "__len__") else float(value)}
    link = socket.links[0]
    component = None
    if link.from_node.type == "SEPARATE_COLOR":
        component = link.from_socket.name
        link = link.from_node.inputs[0].links[0]
    if link.from_node.type != "TEX_IMAGE" or link.from_node.image is None:
        raise ValueError(f"{socket.name}: require a direct image or a separated image channel")
    return {"image": image_record(link.from_node.image, images), "component": component}


def inventory(objects):
    graph = bpy.context.evaluated_depsgraph_get()
    records, materials, images, corners = {}, {}, {}, {}
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            if not mesh.loop_triangles:
                raise ValueError(f"Empty mesh: {obj.name}")
            points = np.array([list(evaluated.matrix_world @ v.co) for v in mesh.vertices])
            faces = Counter()
            for tri in mesh.loop_triangles:
                mat = evaluated.material_slots[tri.material_index].material if evaluated.material_slots else None
                if mat is None:
                    raise ValueError(f"Missing triangle material in {obj.name}")
                faces[mat.name] += 1
                if mat.name not in materials:
                    node = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                    materials[mat.name] = {name: channel_record(node.inputs[name], images) for name in CHANNELS}
            uv, corners[obj.name] = uv_record(mesh, points)
            records[obj.name] = {"bounds": bounds(points), "gltf_bounds": bounds(points @ AXIS.T),
                                 "triangles": len(mesh.loop_triangles), "material_triangles": dict(faces),
                                 "uv": uv}
        finally:
            evaluated.to_mesh_clear()
    if not records:
        raise ValueError("No mesh objects to audit")
    return {"objects": records, "materials": materials}, corners


def read_glb(path):
    data = path.read_bytes()
    magic, version, size = struct.unpack_from("<4sII", data)
    if (magic, version, size) != (b"glTF", 2, len(data)):
        raise ValueError("Invalid GLB v2 header")
    length, tag = struct.unpack_from("<I4s", data, 12)
    if tag != b"JSON":
        raise ValueError("Missing first GLB JSON chunk")
    doc = json.loads(data[20:20+length])
    offset = 20 + length
    binary_length, binary_tag = struct.unpack_from("<I4s", data, offset)
    if binary_tag != b"BIN\x00" or offset+8+binary_length != len(data):
        raise ValueError("Invalid GLB binary chunk")
    buffers = doc["buffers"]
    if len(buffers) != 1 or "uri" in buffers[0] or not 0 <= binary_length-buffers[0]["byteLength"] <= 3:
        raise ValueError("Expected one embedded GLB buffer")
    return doc, memoryview(data)[offset+8:]


def node_matrix(node):
    if "matrix" in node:
        raw = node["matrix"]
        return Matrix([raw[i:i+4] for i in range(0, 16, 4)]).transposed()
    x, y, z, w = node.get("rotation", (0, 0, 0, 1))
    return Matrix.LocRotScale(Vector(node.get("translation", (0, 0, 0))), Quaternion((w, x, y, z)),
                              Vector(node.get("scale", (1, 1, 1))))


def raw_inventory(path):
    doc, data = read_glb(path)
    records = {}

    def visit(index, parent):
        node = doc["nodes"][index]
        matrix = parent @ node_matrix(node)
        if "mesh" in node:
            name = node["name"]
            if name in records:
                raise ValueError(f"Duplicate GLB mesh node {name}")
            chunks = []
            for primitive in doc["meshes"][node["mesh"]]["primitives"]:
                attrs = primitive["attributes"]
                if "TEXCOORD_0" not in attrs or "indices" not in primitive or primitive.get("mode", 4) != 4:
                    raise ValueError(f"{name}: expected indexed triangle geometry with TEXCOORD_0")
                acc = doc["accessors"][attrs["POSITION"]]
                if acc["componentType"] != 5126 or acc["type"] != "VEC3" or "sparse" in acc:
                    raise ValueError("Raw axis check requires dense FLOAT POSITION")
                view = doc["bufferViews"][acc["bufferView"]]
                offset = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
                positions = np.ndarray((acc["count"], 3), dtype="<f4", buffer=data, offset=offset,
                                       strides=(view.get("byteStride", 12), 4))
                chunks.append(positions @ np.asarray(matrix.to_3x3()).T + np.asarray(matrix.translation))
            records[name] = bounds(np.concatenate(chunks))
        for child in node.get("children", []):
            visit(child, matrix)

    for root in doc["scenes"][doc.get("scene", 0)]["nodes"]:
        visit(root, Matrix.Identity(4))
    embedded = []
    for img in doc.get("images", []):
        view = doc["bufferViews"][img["bufferView"]]
        start = view.get("byteOffset", 0)
        end = start + view["byteLength"]
        if "uri" in img or view["buffer"] != 0 or not 0 <= start < end <= len(data):
            raise ValueError("Nonembedded or invalid texture image")
        embedded.append({"name": img.get("name"), "mime": img["mimeType"], "bytes": end-start,
                         "sha256": sha256(data[start:end]).hexdigest()})
    return {"mesh_bounds": records, "images": embedded, "extensions": doc.get("extensionsUsed", [])}


def material_equal(a, b):
    if a.keys() != b.keys():
        return False
    return all(
        close(record["constant"], b[channel]["constant"]) if "constant" in record and "constant" in b[channel]
        else record == b[channel]
        for channel, record in a.items()
    )


def summary(records):
    low = np.min([item["bounds"][0] for item in records.values()], axis=0)
    high = np.max([item["bounds"][1] for item in records.values()], axis=0)
    return {"mesh_count": len(records), "triangles": sum(item["triangles"] for item in records.values()),
            "bounds_m": [low.tolist(), high.tolist()], "dimensions_mm": (1000*(high-low)).tolist()}


def verify(source_inventory, glb, *, allow_overlap=False, probes=None):
    source, source_corners = source_inventory
    glb = Path(glb).resolve()
    raw = raw_inventory(glb)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    if len(scene.objects):
        raise RuntimeError("GLB import scene is not empty")
    result = bpy.ops.import_scene.gltf(filepath=str(glb), import_pack_images=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"GLB import failed: {result}")
    imported, imported_corners = inventory([obj for obj in scene.objects if obj.type == "MESH"])
    expected, actual = source["objects"], imported["objects"]
    checks = {"mesh_names": expected.keys() == actual.keys() == raw["mesh_bounds"].keys(),
              "object_types": all(obj.type in {"MESH", "EMPTY"} for obj in scene.objects),
              "material_names": source["materials"].keys() == imported["materials"].keys()}
    for name in sorted(expected.keys() & actual.keys() & raw["mesh_bounds"].keys()):
        a, b = expected[name], actual[name]
        uv_a, uv_b = a["uv"], b["uv"]
        uv_ok = all(uv.get("layers") == 1 and uv["degenerate_triangles"] == 0 and
                    uv["sampled_texels"] > 0 and np.all(np.array(uv["bounds"]) >= -1e-6) and
                    np.all(np.array(uv["bounds"]) <= 1+1e-6) and (allow_overlap or uv["overlap_texels"] == 0)
                    for uv in (uv_a, uv_b))
        checks[name] = {"bounds": close(a["bounds"], b["bounds"]),
                        "gltf_axes": close(a["gltf_bounds"], raw["mesh_bounds"][name]),
                        "triangles": a["triangles"] == b["triangles"],
                        "material_assignment": a["material_triangles"] == b["material_triangles"],
                        "uv": bool(uv_ok and close(uv_a["bounds"], uv_b["bounds"])),
                        "uv_mapping": uv_mapping_equal(source_corners[name], imported_corners[name])}
    for name in sorted(source["materials"].keys() & imported["materials"].keys()):
        checks["material:" + name] = material_equal(source["materials"][name], imported["materials"][name])
    failed = sorted(f"{key}/{check}" for key, result in checks.items() if isinstance(result, dict)
                    for check, passed in result.items() if not passed)
    failed.extend(key for key, result in checks.items() if result is False)
    feature_results = probes(scene) if probes else {}
    failed.extend("feature:" + key for key, record in feature_results.items() if record["passed"] is not True)
    return {"status": "failed" if failed else "passed", "failed_checks": failed, "blender": bpy.app.version_string,
            "glb": {**file_input(glb), "bytes": glb.stat().st_size}, "isolated_scene": True,
            "axes": {"blender": "+Z up, -Y front", "glb": "+Y up, +Z front", "units": "meters"},
            "summary": {"source": summary(expected), "imported": summary(actual)},
            "source": source, "imported": imported, "raw_glb": raw, "checks": checks, "features": feature_results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("collection")
    parser.add_argument("glb", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--allow-uv-overlap", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if args.report.resolve() in {args.source.resolve(), args.glb.resolve()}:
        raise ValueError("Report would overwrite a source file")
    write(args.report, {"status": "running"})
    try:
        bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()), use_scripts=False, load_ui=False)
        if bpy.context.scene.unit_settings.scale_length != 1:
            raise ValueError("Expected one Blender unit per meter")
        collection = bpy.data.collections[args.collection]
        report = verify(inventory([obj for obj in collection.all_objects if obj.type == "MESH"]), args.glb,
                        allow_overlap=args.allow_uv_overlap)
    except Exception as exc:
        write(args.report, {"status": "failed", "error": str(exc)})
        raise
    write(args.report, report)
    if report["status"] != "passed":
        raise RuntimeError(f"GLB failed: {report['failed_checks']}")
