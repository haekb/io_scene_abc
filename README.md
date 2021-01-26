# io_scene_lithtech

This addon is forked from [io_scene_abc](https://github.com/cmbasnett/io_scene_abc), renamed to io_scene_lithtech due to the increased scope. 

This addon provides limited support for importing and exporting various Lithtech models formats from [No One Lives Forever](https://en.wikipedia.org/wiki/The_Operative:_No_One_Lives_Forever) to and from Blender 2.8x.

## How To Install

Download or clone the repository, and zip up the `src` folder. Go to `Edit -> Preferences` in Blender 2.8x, select `install` and then select the zip file you just created.

To download the respository, click the green `Code -> Download ZIP` at the top of the main page.

...or grab a release zip if one is there!

## Supported Formats

Format | Import | Export
--- | --- | ---
ABC | Rigid and Skeletal | Limited
LTA | No | Rigid and Skeletal
LTB (PS2) | Rigid and Skeletal | No
LTB (PC) | Rigid and Skeletal | No

The ABC file format description can be found on our wiki [here](https://github.com/cmbasnett/io_scene_abc/wiki/ABC).

Additional format information can be found in [here](https://github.com/haekb/io_scene_lithtech/tree/master/research)

## Known Issues
 - In order to export you must have a mesh, a armature hooked up, and at least one animation action setup
 - Socket locations are a tad off in Blender (They're fine in engine.)
 - Imported skeletal meshes are mirrored on the X axis (They're flipped back on export!)
 - Converters may not provide 1:1 source files
 - Converters don't convert lods!

![](https://raw.githubusercontent.com/haekb/io_scene_lithtech/master/doc/readme/example.png)

## Credits
* **Colin Basnett** - Programming
* **ReindeerFloatilla** - Research
* **Haekb** - Programming / Research