Puzzle & Dragons Texture Tool
======

The Puzzle & Dragons Texture Tool is a python script which extracts texture images from the binary data of the popular iOS & Android game "Puzzle & Dragons" (also known as "Puzzle and Dragons" or simply "PAD".)

Example Usage
------

You can use the Puzzle & Dragons Texture Tool to extract texture data from Puzzle & Dragons' .apk file. For example:

`python PADTextureTool.py padEN.apk`

You can also use it to extract monster textures from .bc files you download from your phone:

`python PADTextureTool.py mons_1262.bc`

By default, the Puzzle & Dragons Texture Tool writes any extracted textures into the same directory as the input file. You can use the `--outdir` argument to specify an output folder of your choosing:

`python PADTextureTool.py mons_1262.bc --outdir "Extracted Textures"`

Acknowledgements
------

Special thanks to Johann C. Rocholl who wrote the open-source [PyPNG](https://pythonhosted.org/pypng/index.html) library which the Puzzle & Dragons Texture Tool uses to output PNG files.