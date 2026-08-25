# FAQ

This this the FAQ page of Installer Resources Extractor.

## Q: How do I save the verbose output to a file?

Here is how: you add `> /path/to/the/output/file.log` to the end of the call. This might remove the text from the screen, but it will save it. this is a great way to collect data to attach to a issue to help me debug the issue.

## Q: What files can Installer Resources Extractor extract?

Installer Resources Extractor is designed to extract resources from macOS installer payload files, including payloads that use Apple's PBZX compression format. It can reconstruct the original payload and extract the files contained inside it.

## Q: Where does the extracted data go?

The extracted files are placed directly in the output directory that you select. The extractor does not create an additional directory containing the payload's original absolute path.

For example, if you select:

`~/Desktop/Extracted`

the extracted files will appear underneath that directory.

## Q: Why does the extracted payload create a Folder named payload.0XX.xxxxx?

That is normal. The extractor is using that as a temperary directory for the payload file that it is currectly extracting. this will get removed when it is done.

## Q: What is PBZX?

PBZX is a packaging format used by macOS installers. It stores data in a sequence of compressed and uncompressed blocks.

Installer Resources Extractor reconstructs these blocks into the original payload before extracting its contents.

## Q: Why does the extractor sometimes report `RAW` blocks?

Not every PBZX block is compressed. Some blocks are stored directly as raw data.

The extractor detects this and copies raw blocks directly into the reconstructed payload instead of attempting to decompress them.

## Q: Why do some blocks use XZ compression?

PBZX payloads can contain blocks compressed with XZ. These blocks are decompressed during reconstruction.

You may see output such as:

`XZ uncomp=8,388,608 stored=4,456,556`

This means that the compressed block occupied 4,456,556 bytes in the installer and expanded to 8,388,608 bytes in the reconstructed payload.

## Q: Why is the reconstructed file much larger than the original payload?

Compression is the reason. The installer payload contains compressed blocks, so the reconstructed payload can be substantially larger than the original file.

For example, a payload that is around 600 MB on disk can reconstruct into several gigabytes of uncompressed data.

## Q: Why can't after the extraction is done, can't the extracted apps open?

When you extract the apps, frameworks, etc. the binaries that drive them can't run because then don't have permission, you need to navigate inside the bundle and run chmod +x on the binary to allow it to run.

## Q: Why does the extractor take a while to finish?

Large macOS installer payloads can contain billions of bytes of data. Reconstructing the payload requires reading every block and decompressing the compressed ones.

The amount of time required depends on the size of the payload, the compression used, and the speed of the computer's storage.

## Q: Can I see what the extractor is doing?

Yes. Run the extractor with verbose output enabled. The extractor will print information about the blocks it discovers and the extraction process.

Verbose output is especially useful when reporting a problem.

## Q: How do I report a problem?

First, run the extractor with verbose output enabled (-v) and save the output to a file:

`extractor ... > /path/to/output.log`

Then attach the log file to your issue report along with information about which macOS installer and payload you were processing.

## Q: The extractor failed. Does that mean my installer is corrupted?

Not necessarily.

macOS installer payloads can contain different formats and structures depending on the version of macOS. An extraction failure may indicate an unsupported format or an issue in the extractor rather than a corrupt installer.

If this happens, save the verbose output and include it in an issue report.

## Q: Can I extract only one file from a payload?

Currently, the normal extraction process reconstructs the payload and extracts its contents. If you only need a particular file, you can extract the payload first and then locate the file in the resulting output directory.

## Q: Does the extractor modify the original payload?

No. The original payload is used as the input and is not modified during extraction.

The reconstructed payload and extracted files are written to the output location instead.

## Q: Can I run the extractor on multiple payload files?

Yes, Each payload from the installer is extracted and placed into the selected output directory.

## Q: What should I do if I get a permission error?

Make sure that you have permission to read the installer app and write to the selected output directory.

Using a directory inside your home folder, such as `~/Desktop` or `~/Documents`, can help avoid unnecessary permission problems.

## Q: Why are there `.DS_Store` files in my extracted directory?

`.DS_Store` files are macOS Finder metadata files. They created during the extraction by macOS and can therefore appear in the extracted output.

They are generally not part of the macOS system resources that you are looking for.

## Q: What information should I include when opening an issue?

Please include:

- The macOS version the installer came from.
- The name of the payload being extracted.
- The version of Installer Resources Extractor.
- Your operating system and architecture.
- The command or options you used.
- The complete verbose log, if possible.
- The error message.
- Whether the failure occurred during PBZX reconstruction or archive extraction.

This information makes it much easier to reproduce and diagnose the problem.
	
