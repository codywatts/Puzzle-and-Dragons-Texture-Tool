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

# This class represents a packed pixel encoding.
class Encoding:
	def __init__(self, channels = None):
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
RAW = Encoding()

# This class represents an instance of a texture.
class Texture:
	def __init__(self, width, height, name, buffer, encoding):
		self.width = width
		self.height = height
		self.name = name
		self.buffer = buffer
		self.encoding = encoding
		self.packedPixels = None
		
		if self.encoding.packedPixelFormat:
			packedPixelFormat = self.encoding.packedPixelFormat.format(self.width * self.height)
			self.packedPixels = struct.unpack(packedPixelFormat, self.buffer)

# This class writes Texture objects to disk.
class TextureWriter:
	# Build the bit-depth conversion table
	bitDepthConversionTable = [[[0 for i in range(256)] for j in range(9)] for k in range(9)]
	for currentBitDepth in range(1, 9):
		for newBitDepth in range(currentBitDepth, 9):
			for value in range(2 ** currentBitDepth):
				bitDepthConversionTable[currentBitDepth][newBitDepth][value] = int(round(value * (float((2 ** newBitDepth) - 1) / float((2 ** currentBitDepth) - 1))))
	
	@classmethod
	def unpackPixels(cls, texture, targetBitDepth):
		bitsPerChannel = texture.encoding.channels
		bitShifts = [sum(bitsPerChannel[channelIndex + 1:]) for channelIndex, channelBitCount in enumerate(bitsPerChannel)]
		bitMasks = [(((2 ** bitCount) - 1) << bitShift) for bitCount, bitShift in zip(bitsPerChannel, bitShifts)]
		conversionTables = [cls.bitDepthConversionTable[currentBitCount][targetBitDepth] for currentBitCount in bitsPerChannel]
		zippedChannelInfo = list(zip(bitShifts, bitMasks, conversionTables))
		
		return [conversionTable[(packedPixelValue & bitMask) >> bitShift] for packedPixelValue in texture.packedPixels for bitShift, bitMask, conversionTable in zippedChannelInfo]
	
	@classmethod
	def exportToImageFile(cls, texture, outputFilePath):
		width, height = texture.width, texture.height
		
		if (width > 0 and height > 0):
			outputDirectory = os.path.dirname(outputFilePath)
			if not os.path.isdir(outputDirectory):
				os.makedirs(outputDirectory)
			
			with open(outputFilePath, 'wb') as outputFileHandle:
				if texture.encoding != RAW:
					targetBitDepth = 8
					flatPixelArray = cls.unpackPixels(texture, targetBitDepth)
					w = png.Writer(width, height, alpha=texture.encoding.hasAlpha, greyscale=texture.encoding.isGreyscale, bitdepth=targetBitDepth, planes=len(texture.encoding.channels))
					w.write_array(outputFileHandle, flatPixelArray)
				
				else:
					outputFileHandle.write(texture.buffer)

# This class translates binary data into Texture objects.
class TextureReader:
	encryptedTextureMagicString = struct.pack("<5B", 0x49, 0x4F, 0x53, 0x43, 0x68) # "IOSCh"
	encryptedTextureHeaderFormat = "<5sBxxxxxx"
	encryptedTextureHeaderFormatSize = struct.calcsize(encryptedTextureHeaderFormat)
	unencryptedTextureMagicString = struct.pack("<3B", 0x54, 0x45, 0x58) # "TEX"
	textureBlockHeaderFormat = "<3sxB11x"
	textureBlockHeaderSize = struct.calcsize(textureBlockHeaderFormat)
	textureBlockHeaderAlignment = 16
	textureManifestFormat = "<IHH24s"
	textureManifestSize = struct.calcsize(textureManifestFormat)
	
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
	# Encoding 0xD is used for raw file data. Typically this JPEG data, but in theory it could be anything.
	encodings[0xD] = RAW
	
	@classmethod
	def decryptAndDecompressBinaryBlob(cls, binaryBlob):
		magicString, decryptionKey = struct.unpack_from(cls.encryptedTextureHeaderFormat, binaryBlob)
		
		if magicString != cls.encryptedTextureMagicString:
			return binaryBlob
		
		# XOR each byte using the decryption key
		binaryBlob = bytearray(byte ^ decryptionKey for byte in bytearray(binaryBlob[cls.encryptedTextureHeaderFormatSize:]))
		
		# Inflate
		decompress = zlib.decompressobj(-zlib.MAX_WBITS)
		binaryBlob = decompress.decompress(bytes(binaryBlob))
		binaryBlob += decompress.flush()
		
		return binaryBlob
	
	@classmethod
	def extractTexturesFromBinaryBlob(cls, binaryBlob, outputDirectory):
		binaryBlob = cls.decryptAndDecompressBinaryBlob(binaryBlob)
		
		offset = 0x0
		while (offset + cls.textureBlockHeaderSize) < len(binaryBlob):
			magicString, numberOfTexturesInBlock = struct.unpack_from(cls.textureBlockHeaderFormat, binaryBlob, offset)
			if magicString == cls.unencryptedTextureMagicString:
				textureBlockHeaderStart = offset
				textureBlockHeaderEnd = textureBlockHeaderStart + cls.textureBlockHeaderSize
				
				for textureManifestIndex in range(0, numberOfTexturesInBlock):
					textureManifestStart = textureBlockHeaderEnd + (cls.textureManifestSize * textureManifestIndex)
					textureManifestEnd = textureManifestStart + cls.textureManifestSize
					
					startingOffset, width, height, name = struct.unpack(cls.textureManifestFormat, binaryBlob[textureManifestStart:textureManifestEnd])
					
					encodingIdentifier = (width >> 12)
					width = width & 0x0FFF
					height = height & 0x0FFF
					
					encoding = cls.encodings[encodingIdentifier]
					
					byteCount = 0
					if (encoding != RAW):
						byteCount = width * height * encoding.stride
					else:
						name, byteCount = struct.unpack("<20sI", name)
					
					name = name.rstrip(b'\0').decode(encoding='UTF-8')
					
					imageDataStart = textureBlockHeaderStart + startingOffset
					imageDataEnd = imageDataStart + byteCount
					offset = max(offset, imageDataEnd & ~(cls.textureBlockHeaderAlignment - 1))
					
					yield Texture(width, height, name, binaryBlob[imageDataStart:imageDataEnd], encoding)
			
			offset += cls.textureBlockHeaderAlignment

def main():
	if (len(sys.argv) <= 1):
		print("Usage: " + os.path.basename(__file__) + " filename")
		sys.exit()
	
	inputFilePath = sys.argv[1]
	
	outputDirectoryPath = os.path.basename(inputFilePath) + " textures"
	
	if zipfile.is_zipfile(inputFilePath):
		with zipfile.ZipFile(inputFilePath, 'r') as apkFile:
			fileContents = apkFile.read('assets/DATA001.BIN')
	
	else:
		with open(inputFilePath, 'rb') as binaryFile:
			fileContents = binaryFile.read()
	
	filesWritten = dict()
	
	for texture in TextureReader.extractTexturesFromBinaryBlob(fileContents, inputFilePath):
		outputFileName = texture.name
		try:
			filesWritten[outputFileName] += 1
			outputFileWithoutExtension, outputFileExtension = os.path.splitext(outputFileName)
			outputFileName = "{} ({}){}".format(outputFileWithoutExtension, filesWritten[outputFileName], outputFileExtension)
		except KeyError:
			filesWritten[outputFileName] = 0
		
		outputFilePath = os.path.join(outputDirectoryPath, outputFileName)
		TextureWriter.exportToImageFile(texture, outputFilePath)

if __name__ == "__main__":
	main()