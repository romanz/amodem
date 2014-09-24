# Audio Modem Communication Library

[![Build Status](https://travis-ci.org/romanz/amodem.svg?branch=master)](https://travis-ci.org/romanz/amodem)
[![Coverage Status](https://coveralls.io/repos/romanz/amodem/badge.png?branch=master)](https://coveralls.io/r/romanz/amodem?branch=master)

# Description

This program can be used to transmit a specified file between 2 computers, using
a simple audio cable (for better SNR and higher speeds) or a simple headset,
allowing true air-gapped communication (via a speaker and a microphone).

The sender modulates an input binary data file into an 32kHz audio file, 
which is played to the sound card, using `aplay` Linux utility.

The receiver side uses `arecord` Linux utility to record the transmitted audio
to an audio file, which is demodulated concurrently into an output binary data file.

The process requires a single manual calibration step: the transmitter has to
find maximal output volume for its sound card, which will not saturate the
receiving microphone.

The modem is using OFDM over an audio cable with the following parameters:

- Sampling rate: 32 kHz
- BAUD rate: 1 kHz
- Symbol modulation: 64-QAM
- Carriers: (1,2,3,4,5,6,7,8) kHz

This way, modem achieves 48kpbs bitrate = 6.0 kB/s.

A simple CRC-32 checksum is used for data integrity verification on each 1KB data frame.


# Installation

Run the following command (will also download and install `numpy` and `bitarray` packages):

	$ sudo pip install amodem

For graphs and visualization (optional), install:

	$ sudo pip install matplotlib

# Calibration

Connect the audio cable between the sender and the receiver, and run the
following scripts:

- On the sender's side:
```
~/sender $ amodem send --calibrate
```

- On the receiver's side:
```
~/receiver $ amodem recv --calibrate
```

Increase the sender computer's output audio level, until the
received **amplitude** and **peak** values are not higher than 0.5, 
while the **coherence** is 1.0 (to avoid saturation).

# Testing

- Prepare the sender (generate random binary data file to be sent):

```
~/sender $ dd if=/dev/urandom of=data.tx bs=125kB count=1 status=none
~/sender $ sha256sum data.tx
008df57d4f3ed6e7a25d25afd57d04fc73140e8df604685bd34fcab58f5ddc01  data.tx
```

- Start the receiver:
```
~/receiver $ amodem recv >data.rx
```

- Start the sender:
```
~/sender $ amodem send <data.tx
```

- After the receiver has finished, verify that the file's hash is the same:
```
~/receiver $ sha256sum data.rx
008df57d4f3ed6e7a25d25afd57d04fc73140e8df604685bd34fcab58f5ddc01  data.rx
```

# Visualization
Make sure that `matplotlib` package is installed, and run (at the receiver side):

```
 ~/receiver $ amodem recv --plot >data.rx
```
