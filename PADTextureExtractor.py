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

from __future__ import (absolute_import, division, print_function)

import os
import png
import struct
import sys
import zipfile
import zlib

class Encoding:
	def __init__(self, channels = None, packedPixelFormat = None, hasAlpha = None, isGreyscale = None):
		self.channels = channels
		if self.channels:
			self.stride = (sum(self.channels) // 8)
			self.hasAlpha = (len(self.channels) == 4)
			self.isGreyscale = (len(self.channels) == 1)
			self.packedPixelFormat = dict({4: ">{}L", 2: "<{}H", 1: "<{}B"})[self.stride]
		else:
			self.stride = None
			self.hasAlpha = None
			self.isGreyscale = None
			self.packedPixelFormat = None

R8G8B8A8 = Encoding([8, 8, 8, 8])
R5G6B5 = Encoding([5, 6, 5])
R4G4B4A4 = Encoding([4, 4, 4, 4])
R5G5B5A1 = Encoding([5, 5, 5, 1])
L8 = Encoding([8])
JPEG = Encoding()

class Texture:
	def __init__(self, width, height, name, buffer, encoding):
		self.width = width
		self.height = height
		self.name = name
		self.buffer = buffer
		self.encoding = encoding

	def exportToImageFile(self, fileName, outputDirectory):
		if not os.path.isdir(outputDirectory):
			os.makedirs(outputDirectory)
		
		with open(os.path.join(outputDirectory, fileName), 'wb') as outputFile:
			if self.encoding != JPEG:
				packedPixelFormat = self.encoding.packedPixelFormat.format(self.width * self.height)
				unpackedImageData = struct.unpack(packedPixelFormat, self.buffer)
				imageByteArray = [0] * self.width * self.height * len(self.encoding.channels)
				for pixelIndex, pixelValue in enumerate(unpackedImageData):
					for channelIndex, bitCount in reversed(list(enumerate(self.encoding.channels))):
						bitMask = ((2 ** bitCount) - 1)
						multiplier = float(255) / float(bitMask)
						channelByte = int(round((pixelValue & bitMask) * multiplier))
						pixelValue = pixelValue >> bitCount
						imageByteArray[pixelIndex * len(self.encoding.channels) + channelIndex] = channelByte
				w = png.Writer(self.width, self.height, alpha=self.encoding.hasAlpha, greyscale=self.encoding.isGreyscale)
				w.write_array(outputFile, imageByteArray)
			
			else:
				outputFile.write(self.buffer)

def decryptAndDecompressBinaryBlob(binaryBlob):
	encryptedTextureMagicString = struct.pack("<5B", 0x49, 0x4F, 0x53, 0x43, 0x68) # "IOSCh"
	encryptedTextureHeaderFormat = "<5sBxxxxxx"
	magicString, decryptionKey = struct.unpack_from(encryptedTextureHeaderFormat, binaryBlob)
	
	if magicString != encryptedTextureMagicString:
		return binaryBlob
	
	# XOR each byte using the decryption key
	binaryBlob = bytearray(byte ^ decryptionKey for byte in bytearray(binaryBlob[struct.calcsize(encryptedTextureHeaderFormat):]))
	
	# Inflate
	decompress = zlib.decompressobj(-zlib.MAX_WBITS)
	binaryBlob = decompress.decompress(bytes(binaryBlob))
	binaryBlob += decompress.flush()
	
	return binaryBlob

def extractTexturesFromBinaryBlob(binaryBlob, outputDirectory):
	binaryBlob = decryptAndDecompressBinaryBlob(binaryBlob)
	
	unencryptedTextureMagicString = struct.pack("<3B", 0x54, 0x45, 0x58) # "TEX"
	offset = binaryBlob.find(unencryptedTextureMagicString)
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
			
			encodingIdentifier = (width >> 12)
			width = width & 0x0FFF
			height = height & 0x0FFF
			
			encodings = dict()
			# Encoding 0x0 is four bytes per pixel; one byte per red, green, blue and alpha channel.
			encodings[0x0] = R8G8B8A8
			# Encoding 0x2 is two bytes per pixel; five bits for the red channel, six bits for the green channel, and five bits for the blue channel.
			encodings[0x2] = R5G6B5
			# Encoding 0x3 is two bytes per pixel; four bits per red, green, blue and alpha channel.
			encodings[0x3] = R4G4B4A4
			# Encoding 0x4 is two bytes per pixel; five bits per red, green, blue channel, and then one bit for the alpha channel.
			encodings[0x4] = R5G5B5A1
			# Encodings 0x8 and 0x9 are one byte per pixel; they are greyscale images.
			encodings[0x8] = L8
			encodings[0x9] = L8
			# Encoding 0xD represents a raw JPEG image.
			encodings[0xD] = JPEG
			
			encoding = encodings[encodingIdentifier]
			
			byteCount = 0
			if (encoding != JPEG):
				byteCount = width * height * encoding.stride
			else:
				name, byteCount = struct.unpack("20sI", name)
			
			name = name.rstrip(b'\0').decode(encoding='UTF-8')
			
			imageDataStart = offset + startingOffset
			imageDataEnd = imageDataStart + byteCount
			
			image = Texture(width, height, name, binaryBlob[imageDataStart:imageDataEnd], encoding)
			image.exportToImageFile(str(offset) + "_" + image.name, outputDirectory + " textures")
		
		offset = binaryBlob.find(unencryptedTextureMagicString, offset + 1)

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