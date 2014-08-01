# Audio Modem for Uni-Directional Communication

This program can be used to transmit a specified file between 2 computers, using
a simple audio cable (for better SNR and higher speeds) or a simple headset,
allowing true air-gapped communication (via a speaker and a microphone).

The sender side uses `send.py` script to modulate the input data into an 32kHz
audio file, which is played to the sound card, using `aplay` Linux utility.

The receiver side uses `arecord` Linux utility to record the transmitted audio
to an audio file, which is demodulated concurrently by the `recv.py` script.

The process requires a single manual calibration step: the transmitter has to
find maximal output volume for its sound card, which will not saturate the
receiving microphone.

The modem is using OFDM over an audio cable with the following parameters:

- Sampling rate: 32 kHz
- BAUD rate: 1 kHz
- Symbol modulation: 64-QAM
- Carriers: (1,2,3,4,5,6,7,8,9) kHz

This way, modem achieves 54kpbs bitrate = 6.75 kB/s.

A simple Reed-Solomon ECC is used, with (255,245) rate = ~3.9% overhead.

# Installation

## Required packages

Make sure the following  Python packages are installed:

	$ sudo pip install numpy reedsolo bitarray

## Calibration

Connect the audio cable between the sender and the receiver, and run the
following script on both of them.

```
$ ./calib.py send  # run on the sender side
$ ./calib.py recv  # run on the receiver side
```

The sender computer's audio level should be increased, until the received
**amplitude** is not higher than 0.5, while the **coherence** is 1.0 (so 
saturation does not happen).

## Testing

`test.sh` script is used to transmit a random data file between two computers
(using SSH connection) and to verify its correct reception.

- Set connection parameters to sending computer:

```
$ export SRC_HOST="sender@tx.host"
$ export SRC_DIR="/home/sender/Code/amodem"
```

- Set connection parameters to receiving computer:

```
$ export DST_HOST="receiver@rx.host"
$ export SRC_DIR="/home/receiver/Code/amodem"
```

- Run the test script:

```
$ ./test.sh
```
