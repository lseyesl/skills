# Asset Libraries and Reuse

Use an asset library when a datablock is meant to be reused across projects. Use linking for centrally maintained read-only data, appending for independent local copies, and library overrides only when linked data needs controlled local edits.

## Prepare a reusable asset

- Choose the asset root: collection for a multi-object prop/character, object for a simple item, material/world/node group for reusable shading or setups.
- Remove accidental dependencies, orphan helpers, broken paths, `.001` names, and preview-only objects outside the asset root.
- Use stable origins, real-world scale, meaningful transforms, material slots and exposed node-group inputs.
- Keep external files portable through relative paths or an explicit packed/copy policy.
- Add a useful description, author/source/licence metadata, tags, and a preview that shows scale and purpose.

Most Blender IDs that support assets expose `asset_mark()` and `asset_clear()`:

```python
asset = bpy.data.collections["ASSET_science_submarine"]
asset.asset_mark()
asset.asset_data.description = "Reusable stylized research submarine"
asset.asset_data.tags.new("vehicle")
asset.asset_data.tags.new("underwater")
asset.asset_generate_preview()
```

Discover these methods on the running ID type. Preview generation may require a UI/render-capable session; treat its absence as a recoverable packaging limitation, not permission to invent a preview.

Asset catalogs are library-level metadata, not merely an arbitrary string on one datablock. Preserve existing catalog IDs and catalog-definition files. Do not assign guessed UUIDs or rewrite another user's catalogs.

## Link versus append

Load known datablocks without UI operators:

```python
with bpy.data.libraries.load(str(library_path), link=True) as (source, target):
    if "ASSET_science_submarine" not in source.collections:
        raise KeyError("collection missing from library")
    target.collections = ["ASSET_science_submarine"]

linked = target.collections[0]
bpy.context.scene.collection.children.link(linked)
```

Set `link=False` to append a local independent copy. Inspect `source` names before assigning `target`; never assume the requested datablock exists. Reusing the same library repeatedly should detect an existing matching `library.filepath` and datablock instead of creating duplicates.

- **Link:** centralized updates, smaller files, limited direct edits.
- **Append:** self-contained local copy, no upstream updates.
- **Override:** local edits layered over a linked hierarchy; higher complexity and version sensitivity.

## Library overrides

Overrides depend on hierarchy, instancing and context. Before creating one:

1. inspect the linked root, children, dependencies and existing overrides;
2. confirm the user wants upstream synchronization rather than an appended copy;
3. create the override in an isolated context using the API available in the running Blender;
4. reload the source library and verify intended local edits survive while upstream changes propagate.

Do not make linked data local or resync overrides as a generic repair step. Those operations can sever update paths or discard local edits.

## Packaging and validation

- Save reusable assets to a deliberate `.blend` path without overwriting the current source unexpectedly.
- Check linked library paths and missing external files from both the source asset file and a consuming file.
- Reopen the asset file and append/link it into a disposable scene.
- Confirm the root, hierarchy, materials, node groups, textures, rig/actions and preview are available.
- Report whether dependencies are packed, copied, relative, linked, or intentionally external.
- Preserve asset licences and attribution in metadata or the delivery manifest.
