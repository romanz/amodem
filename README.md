# Audio Modem Communication Library

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
- Carriers: (1,2,3,4,5,6,7,8) kHz

This way, modem achieves 48kpbs bitrate = 6.0 kB/s.

A simple Reed-Solomon ECC is used, with (255,245) rate = ~3.9% overhead.

# Installation

## Required packages

Make sure the following  Python packages are installed:

	$ sudo pip install numpy reedsolo bitarray

For graphs and visualization (optional), install:

	$ sudo pip install matplotlib

## Calibration

Connect the audio cable between the sender and the receiver, and run the
following scripts:

- On the sender's side:
```
~/sender/amodem $ ./calib.py send 
```

- On the receiver's side:
```
~/receiver/amodem $ ./calib.py recv
```

The sender computer's output audio level should be increased, until the 
received **amplitude** and **peak** values are not higher than 0.5, while
the **coherence** is 1.0 (to avoid saturation).

See http://youtu.be/iCg1tepGz10 for calibration demo.

## Testing

See http://youtu.be/94yS3IZmtho for usage demo.

- Prepare the sender:

```
~/sender/amodem $ dd if=/dev/urandom of=data.send bs=125kB count=1 status=none
~/sender/amodem $ ./send.py <data.send >audio.pcm
2014-08-01 21:00:06,723 INFO         Running MODEM @ 48.0 kbps
2014-08-01 21:00:06,773 INFO         3.210 seconds of training audio
2014-08-01 21:00:07,712 DEBUG             8.886 seconds of data audio
2014-08-01 21:00:08,714 DEBUG            14.941 seconds of data audio
2014-08-01 21:00:09,712 DEBUG            20.994 seconds of data audio
2014-08-01 21:00:10,381 INFO         21.846 seconds of data audio, for 125.000 kB of data
~/sender/amodem $ sha256sum data.send
008df57d4f3ed6e7a25d25afd57d04fc73140e8df604685bd34fcab58f5ddc01  data.send
```

- Start the receiver:
```
~/receiver/amodem $ ./wave.py record rx.int16 &
~/receiver/amodem $ ./recv.py <rx.int16 >data.recv
2014-08-01 21:00:30,068 INFO         Running MODEM @ 48.0 kbps
2014-08-01 21:00:30,068 DEBUG        Skipping first 0.100 seconds
```

- Start the sender:
```
~/sender/amodem $ ./wave.py play audio.pcm 
```

- The receiver should print similar messages during demodulation:
```
2014-08-01 21:00:34,847 INFO         Carrier detected at ~4910.0 ms @ 1.0 kHz: coherence=99.991%, amplitude=0.485
2014-08-01 21:00:34,847 DEBUG        Buffered 1000 ms of audio
2014-08-01 21:00:34,883 INFO         Carrier starts at 4909.844 ms
2014-08-01 21:00:35,447 INFO         Prefix OK
2014-08-01 21:00:35,656 DEBUG        Current phase on carrier: 0.260
2014-08-01 21:00:35,656 DEBUG        Excepted phase on carrier: 0.250
2014-08-01 21:00:35,657 INFO         Frequency error: -13.24 ppm
2014-08-01 21:00:35,657 INFO         Sampling error: 0.31 samples
2014-08-01 21:00:36,623 INFO                1.0 kHz: Noise sigma=0.0030, SNR=50.4 dB
2014-08-01 21:00:36,627 INFO                2.0 kHz: Noise sigma=0.0025, SNR=52.0 dB
2014-08-01 21:00:36,631 INFO                3.0 kHz: Noise sigma=0.0021, SNR=53.5 dB
2014-08-01 21:00:36,636 INFO                4.0 kHz: Noise sigma=0.0029, SNR=50.8 dB
2014-08-01 21:00:36,643 INFO                5.0 kHz: Noise sigma=0.0038, SNR=48.3 dB
2014-08-01 21:00:36,649 INFO                6.0 kHz: Noise sigma=0.0046, SNR=46.7 dB
2014-08-01 21:00:36,657 INFO                7.0 kHz: Noise sigma=0.0053, SNR=45.5 dB
2014-08-01 21:00:36,664 INFO                8.0 kHz: Noise sigma=0.0066, SNR=43.6 dB
2014-08-01 21:00:36,840 INFO         Demodulation started
2014-08-01 21:00:37,591 DEBUG               6.0 kB, realtime:  75.04%, sampling error: +0.052%
2014-08-01 21:00:38,576 DEBUG              12.0 kB, realtime:  86.78%, sampling error: +0.069%
2014-08-01 21:00:39,522 DEBUG              18.0 kB, realtime:  89.38%, sampling error: +0.085%
2014-08-01 21:00:40,669 DEBUG              24.0 kB, realtime:  95.72%, sampling error: +0.085%
2014-08-01 21:00:41,510 DEBUG              30.0 kB, realtime:  93.39%, sampling error: +0.083%
2014-08-01 21:00:42,587 DEBUG              36.0 kB, realtime:  95.79%, sampling error: +0.082%
2014-08-01 21:00:43,586 DEBUG              42.0 kB, realtime:  96.37%, sampling error: +0.087%
2014-08-01 21:00:44,547 DEBUG              48.0 kB, realtime:  96.33%, sampling error: +0.064%
2014-08-01 21:00:45,594 DEBUG              54.0 kB, realtime:  97.27%, sampling error: +0.071%
2014-08-01 21:00:46,652 DEBUG              60.0 kB, realtime:  98.12%, sampling error: +0.056%
2014-08-01 21:00:47,600 DEBUG              66.0 kB, realtime:  97.81%, sampling error: +0.055%
2014-08-01 21:00:48,565 DEBUG              72.0 kB, realtime:  97.71%, sampling error: +0.038%
2014-08-01 21:00:49,618 DEBUG              78.0 kB, realtime:  98.29%, sampling error: +0.029%
2014-08-01 21:00:50,568 DEBUG              84.0 kB, realtime:  98.06%, sampling error: +0.019%
2014-08-01 21:00:51,645 DEBUG              90.0 kB, realtime:  98.70%, sampling error: +0.011%
2014-08-01 21:00:52,588 DEBUG              96.0 kB, realtime:  98.42%, sampling error: +0.002%
2014-08-01 21:00:53,600 DEBUG             102.0 kB, realtime:  98.59%, sampling error: -0.004%
2014-08-01 21:00:54,562 DEBUG             108.0 kB, realtime:  98.46%, sampling error: +0.006%
2014-08-01 21:00:55,541 DEBUG             114.0 kB, realtime:  98.43%, sampling error: -0.002%
2014-08-01 21:00:56,582 DEBUG             120.0 kB, realtime:  98.71%, sampling error: -0.006%
2014-08-01 21:00:57,545 DEBUG             126.0 kB, realtime:  98.60%, sampling error: -0.005%
2014-08-01 21:00:58,371 INFO         EOF encountered
2014-08-01 21:00:58,371 DEBUG        Demodulated 131.070 kB @ 21.531 seconds (98.6% realtime)
2014-08-01 21:00:58,372 INFO         Received 125.000 kB @ 21.531 seconds = 5.806 kB/s
```

- Verify correctness and stop the recording:
```
~/receiver/amodem $ sha256sum data.recv 
008df57d4f3ed6e7a25d25afd57d04fc73140e8df604685bd34fcab58f5ddc01  data.recv
~/receiver/amodem $ killall arecord
``` 

See https://www.dropbox.com/sh/2yai1xmntdqlwf1/AACvfzasKEHK0zVxdzI4jF7pa for complete sender
and receiver snapshot data.