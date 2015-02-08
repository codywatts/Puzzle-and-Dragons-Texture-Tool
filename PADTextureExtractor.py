################################################################################
#
# This script extracts texture images from the binary data of the popular
# mobile game "Puzzle & Dragons".
#
# It was written by Cody Watts.
#
# You can read more about it here: http://www.codywatts.com/padtextureextractor
#
################################################################################

import os
import png
import struct
import sys
import zipfile

class Texture:
	def __init__(self, width, height, name, byteCount, encoding):
		self.width = width
		self.height = height
		self.name = name
		self.byteCount = byteCount
		self.encoding = encoding

	def setBuffer(self, buffer):
		self.buffer = buffer

	def getSizeInBytes(self):
		if self.encoding == 0x0: return self.width * self.height * 4 # Four bytes per pixel
		elif self.encoding == 0x2: return self.width * self.height * 2 # Two bytes per pixel
		elif self.encoding == 0x3: return self.width * self.height * 2 # Two bytes per pixel
		elif self.encoding == 0x4: return self.width * self.height * 2 # Two bytes per pixel
		elif self.encoding == 0x8 or self.encoding == 0x9: return self.width * self.height # One byte per pixel
		elif self.encoding == 0xD: return self.byteCount # Variable number of bytes per pixel
		return 0

	def exportToImageFile(self, fileName, outputDirectory):
		if not os.path.isdir(outputDirectory):
			os.makedirs(outputDirectory)
		
		with open(os.path.join(outputDirectory, fileName), 'wb') as outputFile:
			# Encoding 0x0 is four bytes per pixel; one byte per red, green, blue and alpha channel.
			if self.encoding == 0x0:
				unpackedImageData = struct.unpack("<" + str(self.width * self.height * 4) + "B", self.buffer)
				w = png.Writer(self.width, self.height, alpha=True)
				w.write_array(outputFile, unpackedImageData)
			
			# Encoding 0x2 is two bytes per pixel; five bits for the red channel, six bits for the green channel, and five bits for the blue channel.
			elif self.encoding == 0x2:
				unpackedImageData = struct.unpack("<" + str(self.width * self.height) + "H", self.buffer)
				imageByteArray = []
				for pixel in unpackedImageData:
					redByte = int(round(((pixel & 0xF800) >> 11) * (255 / 31)))
					greenByte = int(round(((pixel & 0x07E0) >> 5) * (255 / 63)))
					blueByte = int(round(((pixel & 0x001F)) * (255 / 31)))
					imageByteArray.extend([redByte, greenByte, blueByte])
				w = png.Writer(self.width, self.height)
				w.write_array(outputFile, imageByteArray)
			
			# Encoding 0x3 is two bytes per pixel; four bits per red, green, blue and alpha channel.
			elif self.encoding == 0x3:
				unpackedImageData = struct.unpack("<" + str(self.width * self.height) + "H", self.buffer)
				imageByteArray = []
				for pixel in unpackedImageData:
					redByte = ((pixel & 0xF000) >> 12) * 17
					greenByte = ((pixel & 0x0F00) >> 8) * 17
					blueByte = ((pixel & 0x00F0) >> 4) * 17
					alphaByte = ((pixel & 0x000F) >> 0) * 17
					imageByteArray.extend([redByte, greenByte, blueByte, alphaByte])
				w = png.Writer(self.width, self.height, alpha=True)
				w.write_array(outputFile, imageByteArray)
			
			# Encoding 0x4 is two bytes per pixel; five bits per red, green, blue channel, and then one bit for the alpha channel.
			elif self.encoding == 0x4:
				unpackedImageData = struct.unpack("<" + str(self.width * self.height) + "H", self.buffer)
				imageByteArray = []
				for pixel in unpackedImageData:
					redByte = int(round(((pixel >> 11) & 0x001F) * (255 / 31)))
					greenByte = int(round(((pixel >> 6) & 0x001F) * (255 / 31)))
					blueByte = int(round(((pixel >> 1) & 0x001F) * (255 / 31)))
					alphaByte = (pixel & 0x0001) * 255
					imageByteArray.extend([redByte, greenByte, blueByte, alphaByte])
				w = png.Writer(self.width, self.height, alpha=True)
				w.write_array(outputFile, imageByteArray)
			
			# Encodings 0x8 and 0x9 are one byte per pixel; they are greyscale images.
			elif self.encoding == 0x8 or self.encoding == 0x9:
				unpackedImageData = struct.unpack("<" + str(self.width * self.height) + "B", self.buffer)
				w = png.Writer(self.width, self.height, greyscale=True)
				w.write_array(outputFile, unpackedImageData)
			
			# Encoding 0xD represents a raw JPEG image.
			elif self.encoding == 0xD:
				outputFile.write(self.buffer)

def extractTexturesFromBinaryBlob(binaryBlob, outputDirectory):
	offset = binaryBlob.find("TEX")
	while offset != -1:
		textureBlockHeaderFormat = "<4xB11x"
		textureBlockHeaderStart = offset
		textureBlockHeaderEnd = textureBlockHeaderStart + struct.calcsize(textureBlockHeaderFormat)
		
		numberOfTexturesInBlock = struct.unpack(textureBlockHeaderFormat, binaryBlob[textureBlockHeaderStart:textureBlockHeaderEnd])[0]
		
		textureManifestFormat = "<IHH24s"
		textureManifestSize = struct.calcsize(textureManifestFormat)
		
		for i in range(0, numberOfTexturesInBlock):
			textureManifestStart = textureBlockHeaderEnd + (textureManifestSize * i)
			textureManifestEnd = textureManifestStart + textureManifestSize
			
			startingOffset, width, height, name = struct.unpack(textureManifestFormat, binaryBlob[textureManifestStart:textureManifestEnd])
			
			encoding = (width >> 12)
			width = width & 0x0FFF
			height = height & 0x0FFF
			
			byteCount = 0
			if (encoding == 0xD):
				byteCount = struct.unpack("I", name[-4:])[0]
				name = name[:-4]
			
			name = name.rstrip('\0')
			
			image = Texture(width, height, name, byteCount, encoding)
			
			imageDataStart = offset + startingOffset
			imageDataEnd = imageDataStart + image.getSizeInBytes()
			
			image.setBuffer(binaryBlob[imageDataStart:imageDataEnd])
			image.exportToImageFile(str(offset) + "_" + image.name, outputDirectory + " textures")
		
		offset = binaryBlob.find("TEX", offset + 1)

def main():
	if (len(sys.argv) <= 1):
		print("Usage: " + os.path.basename(__file__) + " filename")
		sys.exit()
	
	fileName = sys.argv[1]
	
	if zipfile.is_zipfile(fileName):
		with zipfile.ZipFile(fileName, 'r') as apkFile:
			fileContents = apkFile.read('assets/DATA001.BIN')
			extractTexturesFromBinaryBlob(fileContents, fileName)
	
	else:
		with open(fileName, 'rb') as binaryFile:
			fileContents = binaryFile.read()
			extractTexturesFromBinaryBlob(fileContents, fileName)

if __name__ == "__main__":
	main()