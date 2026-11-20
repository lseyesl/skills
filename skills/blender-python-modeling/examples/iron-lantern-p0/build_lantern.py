"""Independent procedural modules for the calibrated hurricane lantern pilot."""

from math import cos, pi, sin, sqrt, tau

import bmesh
import bpy
from mathutils import Vector

from calibrate import HERE, TASK, read
from reference_workspace import reference_landmark


COLORS = {
    "iron": (0.21, 0.24, 0.26, 1),
    "rim": (0.32, 0.36, 0.39, 1),
    "wire": (0.40, 0.42, 0.41, 1),
    "glass": (0.29, 0.47, 0.59, 1),
}
MODULES = {
    "base": ("Turned reservoir", "Stepped reservoir silhouette and ground contact", 1),
    "globe": ("Glass globe", "Bulged globe pinched toward the two cups", 1),
    "cups": ("Globe seats", "Upper and lower turned rims", 2),
    "hood": ("Chimney hood", "Bell lip with raised cylindrical chamber", 1),
    "vent": ("Vent and lid", "Open vent slots between the hood and overhanging lid", 2),
    "supports": ("Side air tubes", "Two swept tubes seated in the reservoir and hood", 2),
    "bail": ("Carrying bail", "Tall wire bail with a raised center bend", 1),
    "lifter": ("Lifting loop", "Small open loop above the lid", 1),
    "cage": ("Globe guard", "Crossed wire guard following the globe", 2),
    "controls": ("Fill cap and adjuster", "Front cap and side adjuster", 2),
}


def anchors(scene):
    annotation = read(HERE / "landmarks.json")
    return {
        view: {group: [reference_landmark(scene, TASK, view, f"{group}.{i}") for i in range(len(points))]
               for group, points in groups.items()}
        for view, groups in annotation.items()
    }


def material(role):
    name = f"{TASK}::{role}"
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = COLORS[role]
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = COLORS[role]
        bsdf.inputs["Metallic"].default_value = 0 if role == "glass" else 0.75
        bsdf.inputs["Roughness"].default_value = 0.16 if role == "glass" else 0.37
        if role == "glass":
            bsdf.inputs["Transmission Weight"].default_value = 0.85
    return mat


def mesh(collection, module, name, vertices, faces, role):
    name = f"{TASK}::{module}::{name}"
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    bm = bmesh.new()
    try:
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(data)
    finally:
        bm.free()
    data.update()
    for face in data.polygons:
        face.use_smooth = len(face.vertices) == 4
    obj = bpy.data.objects.new(name, data)
    obj["lantern_module"] = module
    obj.color = COLORS[role]
    data.materials.append(material(role))
    collection.objects.link(obj)
    return obj


def lathe(collection, module, name, profile, role="iron", depth=1.0):
    n = 64
    vertices = [(r * cos(tau * i / n), depth * r * sin(tau * i / n), z)
                for r, z in profile for i in range(n)]
    faces = [(j*n+i, j*n+(i+1)%n, (j+1)*n+(i+1)%n, (j+1)*n+i)
             for j in range(len(profile)-1) for i in range(n)]
    faces.extend([tuple(reversed(range(n))), tuple(range(len(vertices)-n, len(vertices)))])
    return mesh(collection, module, name, vertices, faces, role)


def interpolate(points):
    padded = [points[0], *points, points[-1]]
    path = []
    for a, b, c, d in zip(padded, padded[1:], padded[2:], padded[3:]):
        for i in range(5):
            t = i / 5
            path.append(0.5 * (2*b + (c-a)*t + (2*a-5*b+4*c-d)*t*t + (-a+3*b-3*c+d)*t*t*t))
    return [*path, points[-1]]


def sweep(collection, module, name, points, radius, role="wire", *, smooth=True, depth=1.0, axis=(0, 1, 0), closed=False):
    path = interpolate(points) if smooth else points
    n = 16
    vertices = []
    axis = Vector(axis)
    for i, point in enumerate(path):
        previous = path[i-1] if closed or i else point
        following = path[(i+1) % len(path)] if closed or i+1 < len(path) else point
        tangent = (following - previous).normalized()
        across = (axis - tangent * axis.dot(tangent)).normalized()
        normal = tangent.cross(across)
        vertices.extend(point + radius*(depth*cos(tau*j/n)*across + sin(tau*j/n)*normal) for j in range(n))
    faces = [(i*n+j, i*n+(j+1)%n, ((i+1)%len(path))*n+(j+1)%n, ((i+1)%len(path))*n+j)
             for i in range(len(path) if closed else len(path)-1) for j in range(n)]
    if not closed:
        faces.extend([tuple(reversed(range(n))), tuple(range(len(vertices)-n, len(vertices)))])
    obj = mesh(collection, module, name, vertices, faces, role)
    obj["cap_ring_size"] = n
    return obj


def vent_shell(collection, r, low, window_bottom, window_top, high):
    # A ring of volumetric cells. Emit only boundary faces, leaving open windows
    # between posts and no coincident faces between neighboring solid cells.
    count = 64
    rings = (low, window_bottom, window_top, high)
    vertices = [(radius*cos(tau*i/count), radius*sin(tau*i/count), z)
                for z in rings for radius in (r-0.0013, r) for i in range(count)]

    def index(level, outer, i):
        return (2*level + outer)*count + i % count

    def solid(level, i):
        return 0 <= level < 3 and (level != 1 or i % 8 in (0, 7))

    faces = []
    for k in range(3):
        for i in range(count):
            if not solid(k, i):
                continue
            a, b, c, d = (index(k, 0, i), index(k, 0, i+1), index(k+1, 0, i+1), index(k+1, 0, i))
            A, B, C, D = (index(k, 1, i), index(k, 1, i+1), index(k+1, 1, i+1), index(k+1, 1, i))
            faces.extend([(a, b, c, d), (D, C, B, A)])
            for neighbor, face in [((k, i-1), (d, D, A, a)), ((k, i+1), (b, B, C, c)),
                                   ((k-1, i), (a, A, B, b)), ((k+1, i), (c, C, D, d))]:
                if not solid(*neighbor):
                    faces.append(face)
    return mesh(collection, "vent", "perforated collar", vertices, faces, "iron")


def profile(points):
    return [(p.x, p.z) for p in points]


def symmetric_path(half):
    return [*half, *(Vector((-p.x, p.y, p.z)) for p in reversed(half[:-1]))]


def build(collection, module, a, params):
    front, right = a["front"], a["right"]
    if module == "base":
        rows = [(p.x * params["base_width"], max(0.0, p.z - front["base"][0].z)) for p in front["base"]]
        lathe(collection, module, "reservoir", rows, depth=right["base"][0].y / front["base"][0].x)
    elif module == "globe":
        depth = right["globe"][0].y / max(p.x for p in front["globe"])
        lathe(collection, module, "glass", profile(interpolate(front["globe"])), "glass", depth)
    elif module == "cups":
        for name in ("cup_lower", "cup_upper"):
            lathe(collection, module, name, profile(front[name]), "rim")
    elif module == "hood":
        lathe(collection, module, "bell", profile(front["hood"]))
    elif module == "vent":
        low, lower, upper, _ = front["vent"]
        vent_shell(collection, upper.x, low.z - 0.001, lower.z, upper.z - 0.0006, upper.z + 0.001)
        lathe(collection, module, "lid", profile(front["lid"]), "rim")
        if params["vent_blocked"]:
            r = upper.x - 0.003
            lathe(collection, module, "diagnostic blocked insert",
                  [(r, lower.z), (r, upper.z - 0.0006)])
    elif module == "supports":
        # The annotated tube is on the left; normalize its magnitude before
        # mirroring. Keep both modeled tubes on their own side of the lantern.
        points = [Vector((abs(p.x), 0, p.z)) for p in front["support"]]
        points[0].x -= 0.004
        points[0].z -= 0.0015
        points[-1].x = front["hood"][4].x + params["hood_seat"]
        radius = 0.0072
        depth = right["support"][0].y / radius
        for side in (-1, 1):
            sweep(collection, module, "left" if side < 0 else "right",
                  [Vector((side*p.x, 0, p.z)) for p in points], radius, "iron", depth=depth)
    elif module in {"bail", "lifter"}:
        points = [p.copy() for p in front[module]]
        if module == "lifter":
            points[0].z -= 0.0015
        sweep(collection, module, "wire", symmetric_path(points), 0.00135 if module == "bail" else 0.00105)
    elif module == "cage":
        wire = interpolate(front["cage"])
        globe = interpolate(front["globe"])
        depth = right["globe"][0].y / max(p.x for p in front["globe"])
        for side in (-1, 1):
            points = []
            for p in wire:
                lo, hi = next((pair for pair in zip(globe, globe[1:]) if pair[0].z <= p.z <= pair[1].z),
                              (globe[-2], globe[-1]))
                r = lo.x + (hi.x-lo.x)*(p.z-lo.z)/(hi.z-lo.z) + 0.0014
                points.append(Vector((side*p.x, -depth*sqrt(max(0.0, r*r-p.x*p.x)), p.z)))
            sweep(collection, module, f"guard {side:+d}", points, 0.00075, smooth=False)
    elif module == "controls":
        center, edge = front["cap"]
        r = edge.x - center.x
        cap = lathe(collection, module, "fill cap", [(r*0.8, 0), (r, 0.003), (r, 0.006), (r*0.9, 0.007)], "rim")
        cap.location = (center.x, right["cap"][0].y + 0.0015, center.z - 0.0065)
        cap.rotation_euler.x = 0.28
        p, q = front["key"]
        stem = [Vector((v.x, -0.004, v.z)) for v in (p, q)]
        sweep(collection, module, "adjuster stem", stem, 0.0015, smooth=False)
        points = [stem[-1] + Vector((0, 0.004*cos(tau*i/24), 0.0055*sin(tau*i/24))) for i in range(24)]
        sweep(collection, module, "adjuster ring", points, 0.0011, smooth=False, axis=(1, 0, 0), closed=True)
    else:
        raise ValueError(f"Unknown module: {module}")


def rebuild(collection, module, a, params):
    for obj in list(collection.objects):
        if obj.get("lantern_module") == module:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data.users == 0:
                bpy.data.meshes.remove(data)
    build(collection, module, a, params)
    bpy.context.view_layer.update()
