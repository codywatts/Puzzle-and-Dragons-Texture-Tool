PAD Texture Extractor
======

The PAD Texture Extractor is a python script which extracts texture images from the binary data of the popular mobile game "Puzzle & Dragons".

Example Usage
------

You can use the PAD Texture Extractor to extract texture data from Puzzle & Dragons' .apk file. For example:

`python PADTextureExtractor.py padEN.apk`

You can also use it to extract monster textures from .bc files you download from your phone:

`python PADTextureExtractor.py mons_1262.bc`

Acknowledgements
------

Special thanks to Johann C. Rocholl who wrote the open-source [PyPNG](https://pythonhosted.org/pypng/index.html) library which the PAD Texture Extractor uses to output PNG files.