<a id="asset-libraries-and-reuse"></a>

# 资产库与复用

在数据块需要在多个项目之间重复使用时，使用资源库。对于集中维护的只读数据，使用链接方式；对于独立的本地副本，使用追加方式。只有在需要控制本地编辑的链接数据时，才使用资源库进行覆盖。

<a id="prepare-a-reusable-asset"></a>

## 准备可复用资产

- 选择多对象的资源根目录：集合prop/character，用于简单项目的对象材质、世界环境、节点用于可重复使用的着色或设置的分组。
- 删除不必要的依赖项、孤立的帮助文件、损坏的路径、`.001`名称，以及资产根目录之外的预览对象。
- 使用稳定的起点、真实世界的规模、有意义的变换、材质槽以及暴露的节点组输入。
- 通过相对路径或明确的 packed/copy 策略，保持外部文件的便携性。
- 添加有用的描述、author/source/licence元数据、标签，以及展示规模和用途的预览。

大多数支持资产的 Blender 标识符都暴露了 `asset_mark()` 和 `asset_clear()`：

```python
asset = bpy.data.collections["ASSET_science_submarine"]
asset.asset_mark()
asset.asset_data.description = "Reusable stylized research submarine"
asset.asset_data.tags.new("vehicle")
asset.asset_data.tags.new("underwater")
asset.asset_generate_preview()
```

了解这些在运行中的 ID 类型上的方法。预览生成可能需要一个 UI/render-capable 会话；将其缺失视为可恢复的包装限制，而不是可以随意创建预览的权限。

资产目录是库级别的元数据，而不仅仅是某个数据块上的任意字符串。请保留现有的目录ID和目录定义文件。不要分配猜测的UUID，也不要重写其他用户的目录。

<a id="link-versus-append"></a>

## 链接与追加

加载已知的数据块，无需用户界面操作：

```python
with bpy.data.libraries.load(str(library_path), link=True) as (source, target):
    if "ASSET_science_submarine" not in source.collections:
        raise KeyError("collection missing from library")
    target.collections = ["ASSET_science_submarine"]

linked = target.collections[0]
bpy.context.scene.collection.children.link(linked)
```

设置`link=False`添加一份本地独立的副本。进行检查`source`命名前分配`target`; 永远不要假设请求的数据块存在。重复使用同一个库应该能够检测到已存在的匹配项。`library.filepath`并且使用数据块而不是创建重复项。

- **链接：** 集中式更新，文件较小，直接编辑受限。
- **追加：** 独立的本地副本，无需进行上游更新。
- **覆盖：** 在链接的层次结构中进行的局部编辑；更复杂的操作，对版本更敏感。

<a id="library-overrides"></a>

## 库覆盖

覆盖取决于层次结构、实例化以及上下文。在创建之前：

1. 检查链接的根节点、子节点、依赖关系以及现有的覆盖设置；
2. 确认用户希望进行上游同步，而不是追加复制；
3. 在独立的上下文中使用运行中的 Blender 中提供的 API 创建覆盖操作；
4. 重新加载源库，并确保在上游更改传播时，预期的本地编辑仍然有效。

请不要将链接数据设为本地存储，也不要将重新同步覆盖操作作为通用的修复步骤。这些操作可能会破坏更新路径或丢弃本地编辑内容。

<a id="packaging-and-validation"></a>

## 打包与验证

- 将可重复使用的资源保存到指定的位置`.blend`在未经当前源文件许可的情况下，直接修改路径。
- 检查源资产文件和消耗文件中的关联库路径以及缺失的外部文件。
- 重新打开资源文件，并append/link将其转换为一次性场景。
- 确认根节点、层次结构、材质、节点组、纹理绑定、动作并且提供了预览功能。
- 报告依赖项是否被打包、复制、相对链接，还是故意设置为外部。
- 保留元数据或交付清单中的资产许可和归属信息。
