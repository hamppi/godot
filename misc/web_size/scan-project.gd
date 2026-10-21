extends SceneTree

var classes := {}
var resources := {}
var objects := {}
var all_files: Array[String] = []

func add_class(c: String):
	while not c.is_empty() and ClassDB.class_exists(c):
		classes[c] = true
		c = ClassDB.get_parent_class(c)

func visit(value):
	if value is Resource:
		var id = value.get_instance_id()
		if objects.has(id):
			return
		objects[id] = true
		add_class(value.get_class())
		if value is PackedScene:
			var state = value.get_state()
			for i in state.get_node_count():
				add_class(state.get_node_type(i))
				for j in state.get_node_property_count(i):
					visit(state.get_node_property_value(i, j))
		for prop in value.get_property_list():
			if prop.usage & PROPERTY_USAGE_STORAGE:
				visit(value.get(prop.name))
	elif value is Array:
		for item in value:
			visit(item)
	elif value is Dictionary:
		for key in value:
			visit(value[key])

func load_resource(p: String):
	if resources.has(p):
		return
	resources[p] = true
	for dep in ResourceLoader.get_dependencies(p):
		var bits = dep.split("::")
		var target = bits[bits.size() - 1]
		if target.begins_with("uid://"):
			target = ResourceUID.get_id_path(ResourceUID.text_to_id(target))
		if target.begins_with("res://"):
			load_resource(target)
	var r = load(p)
	if r:
		visit(r)

func find_files(dir: String):
	if FileAccess.file_exists(dir.path_join(".gdignore")):
		return
	for name in DirAccess.get_files_at(dir):
		all_files.append(dir.path_join(name))
	for name in DirAccess.get_directories_at(dir):
		if not name.begins_with(".") and name not in ["web-build", "qa-artifacts"]:
			find_files(dir.path_join(name))

func _initialize():
	var main: String = ProjectSettings.get_setting("application/run/main_scene")
	if main.begins_with("uid://"):
		main = ResourceUID.get_id_path(ResourceUID.text_to_id(main))
	load_resource(main)
	for prop in ProjectSettings.get_property_list():
		if prop.name.begins_with("autoload/"):
			load_resource(str(ProjectSettings.get_setting(prop.name)).trim_prefix("*"))
	find_files("res://")
	for p in all_files:
		# Audio helper scripts choose filenames at runtime. Retain their sound libraries.
		if p.get_extension() in ["ogg", "wav", "mp3"] or p == "res://sample map/map.res":
			load_resource(p)
		if p.ends_with(".gd"):
			var text = FileAccess.get_file_as_string(p)
			var regex = RegEx.new()
			regex.compile("[A-Za-z_][A-Za-z_0-9]*")
			for match in regex.search_all(text):
				add_class(match.get_string())
			regex.compile("res://[^\"\\n]+")
			for match in regex.search_all(text):
				var target = match.get_string()
				if ResourceLoader.exists(target):
					load_resource(target)
	# Match the engine detector's mandatory families; imported/runtime resources need their base loaders.
	for family in ["Font", "InputEvent", "StyleBox", "Window", "ShaderInclude", "Texture", "Material", "Shape2D", "Shape3D"]:
		add_class(family)
		for c in ClassDB.get_inheriters_from_class(family):
			add_class(c)
	for c in ["PackedScene", "GDScript", "Shader", "World2D", "World3D", "Environment", "Image", "ImageTexture", "ImageTexture3D", "ArrayMesh", "ImmediateMesh", "Skin", "Animation", "AnimationLibrary", "AudioStreamOggVorbis", "AudioStreamPlaybackOggVorbis", "OggPacketSequence", "OggPacketSequencePlayback"]:
		add_class(c)
	var disabled: Array[String] = []
	for c in ClassDB.get_class_list():
		if classes.has(c) or c in ["Node", "Resource"]:
			continue
		if not (ClassDB.is_parent_class(c, "Node") or ClassDB.is_parent_class(c, "Resource")):
			continue
		var parent = ClassDB.get_parent_class(c)
		if parent.is_empty() or classes.has(parent):
			disabled.append(c)
	disabled.sort()
	var used = classes.keys()
	used.sort()
	var included = resources.keys()
	included.sort()
	var result = {"used_classes": used, "disabled_classes": disabled, "resources": included}
	var args = OS.get_cmdline_user_args()
	if args.size() > 1:
		var profile = JSON.parse_string(FileAccess.get_file_as_string(args[1]))
		var blocked_classes: Array = profile.get("disabled_classes", [])
		for used_class in classes:
			var c = str(used_class)
			while not c.is_empty():
				if c in blocked_classes:
					push_error("Web template excludes referenced class " + str(used_class) + ". Rebuild its custom template after adding engine features.")
					quit(1)
					return
				c = ClassDB.get_parent_class(c)
		var options = profile.get("disabled_build_options", {})
		if classes.has("JavaScriptBridge") and not options.get("javascript_eval", false):
			push_error("This template omits JavaScriptBridge. Rebuild with javascript_eval=yes for browser SDK access.")
			quit(1)
			return
		for p in resources:
			if str(p).ends_with(".gd") and not options.get("module_gdscript_enabled", false):
				push_error("This template omits GDScript, but the project now uses scripts. Rebuild the template.")
				quit(1)
				return
			if str(p).ends_with(".ogg") and not options.get("module_vorbis_enabled", false):
				push_error("This template omits Vorbis, but the project now uses Ogg audio. Rebuild the template.")
				quit(1)
				return
	var output = args[0] if args.size() else "res://web-dependencies.json"
	var file = FileAccess.open(output, FileAccess.WRITE)
	file.store_string(JSON.stringify(result, "  "))
	print("Scanned ", resources.size(), " resources; enabled ", used.size(), " classes; disabled ", disabled.size(), " class roots")
	quit()
