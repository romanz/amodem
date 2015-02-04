# Audio Modem Communication Library

[![Build Status](https://travis-ci.org/romanz/amodem.svg?branch=master)](https://travis-ci.org/romanz/amodem)
[![Coverage Status](https://coveralls.io/repos/romanz/amodem/badge.png?branch=master)](https://coveralls.io/r/romanz/amodem?branch=master)
[![Code Health](https://landscape.io/github/romanz/amodem/master/landscape.svg)](https://landscape.io/github/romanz/amodem/master)
[![Supported Python Versions](https://pypip.in/py_versions/amodem/badge.svg)](https://pypi.python.org/pypi/amodem/)
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

Get the latest released version from PyPI:

    $ pip install --user amodem

Or, try the latest (unstable) development version from GitHub:

    $ git clone https://github.com/romanz/amodem.git
    $ cd amodem
    $ pip install --user -e .

For graphs and visualization (optional), install `matplotlib` Python package.

For validation, run:

    $ export BITRATE=48  # explicitly select high MODEM bit rate (assuming good SNR).
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
  3000 Hz: good signal
  4000 Hz: good signal
  5000 Hz: good signal
  6000 Hz: good signal
  7000 Hz: good signal
  8000 Hz: good signal
  9000 Hz: good signal
 10000 Hz: good signal
```

If the signal is "too weak", increase the sender's output audio level.

If the signal is "too strong", decrease the sender's output audio level.

If the signal is "too noisy", the SNR is probably too low: decrease the
background noise or increase the signal (without causing saturation).

You can see a video of the calibration process [here](http://www.youtube.com/watch?v=jRUj2Ifk-Po).

# Usage

- Prepare the sender (generate a random binary data file to be sent):

```
~/sender $ dd if=/dev/urandom of=data.tx bs=10KB count=1 status=none
~/sender $ sha256sum data.tx
008df57d4f3ed6e7a25d25afd57d04fc73140e8df604685bd34fcab58f5ddc01  data.tx
```

- Start the receiver (will wait for the sender to start):
```
~/receiver $ amodem-cli recv -vv -i data.rx
```

- Start the sender (will modulate the data and start the transmission):
```
~/sender $ amodem-cli send -vv -o data.tx
```

- A similar log should be emitted by the sender:
```
2015-01-16 11:49:25,181 DEBUG      Audio OFDM MODEM: 48.0 kb/s (64-QAM x 8 carriers) Fs=32.0 kHz                                        amodem-cli:174
2015-01-16 11:49:27,028 INFO       Sending 2.150 seconds of training audio                                                              send.py:63
2015-01-16 11:49:27,029 INFO       Starting modulation                                                                                  send.py:68
2015-01-16 11:49:28,016 DEBUG      Sent      6.000 kB                                                                                   send.py:50
2015-01-16 11:49:28,776 INFO       Sent 10.000 kB @ 1.701 seconds                                                                       send.py:73

```

- A similar log should be emitted by the receiver:
```
2015-01-16 11:49:24,369 DEBUG      Audio OFDM MODEM: 48.0 kb/s (64-QAM x 8 carriers) Fs=32.0 kHz                                        amodem-cli:174
2015-01-16 11:49:24,382 DEBUG      Skipping 0.100 seconds                                                                               recv.py:214
2015-01-16 11:49:24,535 INFO       Waiting for carrier tone: 3.0 kHz                                                                    recv.py:221
2015-01-16 11:49:26,741 INFO       Carrier detected at ~1761.0 ms @ 3.0 kHz: coherence=99.944%, amplitude=0.499                         detect.py:64
2015-01-16 11:49:26,741 DEBUG      Buffered 1000 ms of audio                                                                            detect.py:66
2015-01-16 11:49:26,912 DEBUG      Carrier starts at 1761.000 ms                                                                        detect.py:76
2015-01-16 11:49:26,917 DEBUG      Carrier symbols amplitude : 0.499                                                                    detect.py:101
2015-01-16 11:49:26,917 DEBUG      Current phase on carrier: -0.466                                                                     detect.py:112
2015-01-16 11:49:26,917 DEBUG      Frequency error: -0.01 ppm                                                                           detect.py:113
2015-01-16 11:49:26,917 DEBUG      Frequency correction: 0.005 ppm                                                                      recv.py:225
2015-01-16 11:49:26,917 DEBUG      Gain correction: 2.004                                                                               recv.py:228
2015-01-16 11:49:27,099 DEBUG      Prefix OK                                                                                            recv.py:48
2015-01-16 11:49:27,925 DEBUG        3.0 kHz: SNR = 40.58 dB                                                                            recv.py:92
2015-01-16 11:49:27,925 DEBUG        4.0 kHz: SNR = 41.98 dB                                                                            recv.py:92
2015-01-16 11:49:27,925 DEBUG        5.0 kHz: SNR = 42.81 dB                                                                            recv.py:92
2015-01-16 11:49:27,925 DEBUG        6.0 kHz: SNR = 43.71 dB                                                                            recv.py:92
2015-01-16 11:49:27,926 DEBUG        7.0 kHz: SNR = 43.43 dB                                                                            recv.py:92
2015-01-16 11:49:27,926 DEBUG        8.0 kHz: SNR = 42.96 dB                                                                            recv.py:92
2015-01-16 11:49:27,926 DEBUG        9.0 kHz: SNR = 42.66 dB                                                                            recv.py:92
2015-01-16 11:49:27,926 DEBUG       10.0 kHz: SNR = 42.22 dB                                                                            recv.py:92
2015-01-16 11:49:27,928 INFO       Starting demodulation                                                                                recv.py:119
2015-01-16 11:49:28,008 DEBUG      Got       0.600 kB, realtime:  80.73%, drift: -0.00 ppm                                              recv.py:140
2015-01-16 11:49:28,081 DEBUG      Got       1.200 kB, realtime:  76.60%, drift: -0.00 ppm                                              recv.py:140
2015-01-16 11:49:28,153 DEBUG      Got       1.800 kB, realtime:  75.17%, drift: -0.00 ppm                                              recv.py:140
2015-01-16 11:49:28,224 DEBUG      Got       2.400 kB, realtime:  74.02%, drift: -0.00 ppm                                              recv.py:140
2015-01-16 11:49:28,306 DEBUG      Got       3.000 kB, realtime:  75.72%, drift: -0.00 ppm                                              recv.py:140
2015-01-16 11:49:28,382 DEBUG      Got       3.600 kB, realtime:  75.71%, drift: -0.01 ppm                                              recv.py:140
2015-01-16 11:49:28,458 DEBUG      Got       4.200 kB, realtime:  75.72%, drift: -0.01 ppm                                              recv.py:140
2015-01-16 11:49:28,528 DEBUG      Got       4.800 kB, realtime:  75.10%, drift: -0.01 ppm                                              recv.py:140
2015-01-16 11:49:28,609 DEBUG      Got       5.400 kB, realtime:  75.76%, drift: -0.01 ppm                                              recv.py:140
2015-01-16 11:49:28,686 DEBUG      Got       6.000 kB, realtime:  75.80%, drift: -0.01 ppm                                              recv.py:140
2015-01-16 11:49:28,757 DEBUG      Got       6.600 kB, realtime:  75.36%, drift: -0.01 ppm                                              recv.py:140
2015-01-16 11:49:28,828 DEBUG      Got       7.200 kB, realtime:  75.03%, drift: -0.01 ppm                                              recv.py:140
2015-01-16 11:49:28,909 DEBUG      Got       7.800 kB, realtime:  75.50%, drift: -0.01 ppm                                              recv.py:140
2015-01-16 11:49:28,980 DEBUG      Got       8.400 kB, realtime:  75.15%, drift: -0.01 ppm                                              recv.py:140
2015-01-16 11:49:29,051 DEBUG      Got       9.000 kB, realtime:  74.88%, drift: -0.01 ppm                                              recv.py:140
2015-01-16 11:49:29,261 DEBUG      Got       9.600 kB, realtime:  83.31%, drift: -0.01 ppm                                              recv.py:140
2015-01-16 11:49:29,342 DEBUG      Got      10.200 kB, realtime:  83.23%, drift: -0.01 ppm                                              recv.py:140
2015-01-16 11:49:29,343 DEBUG      EOF frame detected                                                                                   framing.py:57
2015-01-16 11:49:29,343 DEBUG      Demodulated 10.205 kB @ 1.415 seconds (83.2% realtime)                                               recv.py:165
2015-01-16 11:49:29,343 INFO       Received 10.000 kB @ 1.415 seconds = 7.066 kB/s                                                      recv.py:169
```

- After the receiver has finished, verify the received file's hash:
```
~/receiver $ sha256sum data.rx
008df57d4f3ed6e7a25d25afd57d04fc73140e8df604685bd34fcab58f5ddc01  data.rx
```

You can see a video of the data transfer process [here](http://www.youtube.com/watch?v=GZQUtHB8so4).

# Visualization
Make sure that `matplotlib` package is installed, and run (at the receiver side):

```
 ~/receiver $ amodem-cli recv --plot -o data.rx
```


# Donations

Want to donate? Feel free.
Send to [1C1snTrkHAHM5XnnfuAtiTBaA11HBxjJyv](https://blockchain.info/address/1C1snTrkHAHM5XnnfuAtiTBaA11HBxjJyv).

Thanks :)
