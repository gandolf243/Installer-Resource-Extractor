# Installer-Resource-Extractor


## Description

This project is designed to make getting macOS System files, for whatever reason (maybe for restoring support for older hardware) out without installing that version of macOS. This is for Big Sur+ installers, and is designed to run on macOS with the only dependency being the python logging framework. It can be installed using `pip3 install logging` or `python3 -m pip install logging`.
please note: this project takes a while to execute.

## Supported Installers

All installers Big Sur+ are supported, here is a list of tested ones. (if you have tested this program on an installer not checked bellow, please let me know [here](https://github.com/gandolf243/Installer-Resource-Extractor/discussions/1))


- [x] Big Sur 11

- [ ] Monterey 12

- [ ] Ventura 13

- [ ] Sonoma 14

- [ ] Sequoia 15

- [ ] Tahoe 26

- [ ] Golden Gate 27

## Supported macOSes

This project has currently only been tested to run on macOS Sonoma. It most likely will work on way more. Please report [here](https://github.com/gandolf243/Installer-Resource-Extractor/discussions/3) if it runs on a macOS not labeled/checked. This project **will** not work on macOS Sierra (10.12) or earlier, due to `YAA1` (one of the compression formats that apple uses) being introduced in macOS High Sierra (10.13).

- [ ] Big Sur 11

- [ ] Monterey 12

- [ ] Ventura 13

- [x] Sonoma 14

- [ ] Sequoia 15

- [ ] Tahoe 26

- [ ] Golden Gate 27

## Important Links
* [FAQ](./FAQ.md)

## Credits

* [Nathanael Cain](https://github.com/gandolf243)
    * Project Creator and Researcher
    
* [Apple](https://apple.com)
    * [macOS](https://apple.com/macos)
    * PBZX
    * YAA1
