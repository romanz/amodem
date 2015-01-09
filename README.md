# Audio Modem Communication Library

[![Build Status](https://travis-ci.org/romanz/amodem.svg?branch=master)](https://travis-ci.org/romanz/amodem)
[![Coverage Status](https://coveralls.io/repos/romanz/amodem/badge.png?branch=master)](https://coveralls.io/r/romanz/amodem?branch=master)
[![Downloads](https://pypip.in/download/amodem/badge.svg)](https://pypi.python.org/pypi/amodem/)
[![Code Health](https://landscape.io/github/romanz/amodem/master/landscape.svg)](https://landscape.io/github/romanz/amodem/master)
[![Supported Python versions](https://pypip.in/py_versions/amodem/badge.svg)](https://pypi.python.org/pypi/amodem/)
[![License](https://pypip.in/license/amodem/badge.svg)](https://pypi.python.org/pypi/amodem/)

# Description

This program can be used to transmit a specified file between 2 computers, using
a simple audio cable (for better SNR and higher speeds) or a simple headset,
allowing true air-gapped communication (via a speaker and a microphone).

The sender modulates an input binary data file into an 32kHz audio,
which is played to the sound card.

The receiver side records the transmitted audio,
which is demodulated concurrently into an output binary data file.

The process requires a single manual calibration step: the transmitter has to
find maximal output volume for its sound card, which will not saturate the
receiving microphone.

The modem is using OFDM over an audio cable with the following parameters:

- Sampling rate: 32 kHz
- Baud rate: 1 kHz
- Symbol modulation: BPSK, 4-PSK, 16-QAM ,64-QAM
- Carriers: 2-11 kHz

This way, modem may achieve 60kbps bitrate = 7.5 kB/s.

A simple CRC-32 checksum is used for data integrity verification
on each 250 byte data frame.


# Installation

Make sure that `numpy` and `PortAudio v19` packages are installed (on Debian):

    $ sudo apt-get install python-numpy portaudio19-dev

Clone and install latest version:

    $ git clone https://github.com/romanz/amodem.git
    $ pip install --user -e amodem

For graphs and visualization (optional), install `matplotlib` Python package.

For validation, run:

    $ export BITRATE=16  # explicitly select high MODEM bit rate (assuming good SNR).
    $ amodem-cli -h
    usage: amodem-cli [-h] {send,recv} ...

    Audio OFDM MODEM: 48.0 kb/s (64-QAM x 8 carriers) Fs=32.0 kHz

    positional arguments:
      {send,recv}
        send         modulate binary data into audio signal.
        recv         demodulate audio signal into binary data.

    optional arguments:
      -h, --help     show this help message and exit


# Calibration

Connect the audio cable between the sender and the receiver, and run the
following scripts:

- On the sender's side:
```
~/sender $ export BITRATE=48  # explicitly select high MODEM bit rate (assuming good SNR).
~/sender $ amodem-cli send --calibrate
```

- On the receiver's side:
```
~/receiver $ export BITRATE=48  # explicitly select high MODEM bit rate (assuming good SNR).
~/receiver $ amodem-cli recv --calibrate
```

If BITRATE is not set, the MODEM will use 1 kbps settings (single frequency with BPSK modulation).

Change the sender computer's output audio level, until
all frequencies are received well:
```
  1000 Hz: good signal
  2000 Hz: good signal
  3000 Hz: good signal
  4000 Hz: good signal
  5000 Hz: good signal
  6000 Hz: good signal
  7000 Hz: good signal
  8000 Hz: good signal
```

If the signal is "too weak", increase the sender's output audio level.

If the signal is "too strong", decrease the sender's output audio level.

If the signal is "too noisy", the SNR is probably too low: decrease the
background noise or increase the signal (without causing saturation).

# Testing

- Prepare the sender (generate random binary data file to be sent):

```
~/sender $ dd if=/dev/urandom of=data.tx bs=16kB count=1 status=none
~/sender $ sha256sum data.tx
008df57d4f3ed6e7a25d25afd57d04fc73140e8df604685bd34fcab58f5ddc01  data.tx
```

- Start the receiver, which will wait for the sender to start:
```
~/receiver $ amodem-cli recv -vv -i data.rx
```

- Start the sender, which will modulate the data and start the transmission:
```
~/sender $ amodem-cli send -vv -o data.tx
```

- A similar log should be emitted by the sender:
```
2014-10-23 09:46:36,116 DEBUG      MODEM settings: {'F0': 1000.0, 'Nfreq': 8, 'Fs': 32000.0, 'Npoints': 64, 'Tsym': 0.001}              amodem:126
2014-10-23 09:46:36,116 DEBUG      Running: ['aplay', '-', '-q', '-f', 'S16_LE', '-c', '1', '-r', '32000']                              wave.py:20
2014-10-23 09:46:36,665 INFO       Sending 2.150 seconds of training audio                                                              send.py:69
2014-10-23 09:46:36,665 INFO       Starting modulation: <48.000 kbps, 64-QAM, 8 carriers>                                               send.py:74
2014-10-23 09:46:37,735 DEBUG      Sent      6.0 kB                                                                                     send.py:56
2014-10-23 09:46:38,794 DEBUG      Sent     12.0 kB                                                                                     send.py:56
2014-10-23 09:46:39,440 INFO       Sent 16.384 kB @ 2.754 seconds                                                                       send.py:79
```

- A similar log should be emitted by the receiver:
```
2014-10-23 09:46:36,116 DEBUG      MODEM settings: {'F0': 1000.0, 'Nfreq': 8, 'Fs': 32000.0, 'Npoints': 64, 'Tsym': 0.001}              amodem:126
2014-10-23 09:46:36,238 DEBUG      Running: ['arecord', '-', '-q', '-f', 'S16_LE', '-c', '1', '-r', '32000']                            wave.py:20
2014-10-23 09:46:36,408 DEBUG      Skipping 0.128 seconds                                                                               recv.py:275
2014-10-23 09:46:36,409 INFO       Waiting for carrier tone: 1.0 kHz                                                                    recv.py:282
2014-10-23 09:46:37,657 INFO       Carrier detected at ~886.0 ms @ 1.0 kHz: coherence=99.996%, amplitude=0.475                          recv.py:40
2014-10-23 09:46:37,657 DEBUG      Buffered 1000 ms of audio                                                                            recv.py:64
2014-10-23 09:46:37,660 DEBUG      Carrier starts at 9.531 ms                                                                           recv.py:73
2014-10-23 09:46:38,119 DEBUG      Prefix OK                                                                                            recv.py:108
2014-10-23 09:46:38,153 DEBUG      Current phase on carrier: -0.497                                                                     recv.py:121
2014-10-23 09:46:38,153 DEBUG      Frequency error: 0.02 ppm                                                                            recv.py:123
2014-10-23 09:46:38,682 DEBUG        1.0 kHz: SNR = 34.20 dB                                                                            recv.py:165
2014-10-23 09:46:38,715 DEBUG        2.0 kHz: SNR = 35.05 dB                                                                            recv.py:165
2014-10-23 09:46:38,766 DEBUG        3.0 kHz: SNR = 35.52 dB                                                                            recv.py:165
2014-10-23 09:46:38,803 DEBUG        4.0 kHz: SNR = 35.65 dB                                                                            recv.py:165
2014-10-23 09:46:38,837 DEBUG        5.0 kHz: SNR = 35.03 dB                                                                            recv.py:165
2014-10-23 09:46:38,869 DEBUG        6.0 kHz: SNR = 35.05 dB                                                                            recv.py:165
2014-10-23 09:46:38,907 DEBUG        7.0 kHz: SNR = 34.80 dB                                                                            recv.py:165
2014-10-23 09:46:38,943 DEBUG        8.0 kHz: SNR = 33.74 dB                                                                            recv.py:165
2014-10-23 09:46:38,977 INFO       Starting demodulation: <48.000 kbps, 64-QAM, 8 carriers>                                             recv.py:197
2014-10-23 09:46:39,619 DEBUG      Got       6.0 kB, realtime:  64.18%, drift: +0.02 ppm                                                recv.py:215
2014-10-23 09:46:40,538 DEBUG      Got      12.0 kB, realtime:  78.03%, drift: +0.02 ppm                                                recv.py:215
2014-10-23 09:46:41,306 DEBUG      EOF frame detected                                                                                   framing.py:60
2014-10-23 09:46:41,306 DEBUG      Demodulated 16.520 kB @ 2.329 seconds (84.6% realtime)                                               recv.py:244
2014-10-23 09:46:41,306 INFO       Received 16.384 kB @ 2.329 seconds = 7.034 kB/s                                                      recv.py:247
```

- After the receiver has finished, verify that the file's hash is the same:
```
~/receiver $ sha256sum data.rx
008df57d4f3ed6e7a25d25afd57d04fc73140e8df604685bd34fcab58f5ddc01  data.rx
```

# Visualization
Make sure that `matplotlib` package is installed, and run (at the receiver side):

```
 ~/receiver $ amodem-cli recv --plot -o data.rx
```


# Donations

Want to donate? Feel free.
Send to [1C1snTrkHAHM5XnnfuAtiTBaA11HBxjJyv](https://blockchain.info/address/1C1snTrkHAHM5XnnfuAtiTBaA11HBxjJyv).

Thanks :)
