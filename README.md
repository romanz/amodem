# Audio Modem for Air-Gapped Communication #

I am using a simple headset, whose speaker is connected to the transmitting PC and the microphone is connected to the receiving PC.
Then, I bring the speaker and the microphone close together and use the PC's sound cards to perform the communication.

The sender is modulating `data.send` binary file using `send.py` script into 32kHz audio file (`tx.int16`), which is played using `aplay` Linux utility.
The receiver is using `arecord` Linux utility to record the audio file into `rx.int16` 32kHz audio file, which is demodulated by `recv.py` script into `data.recv` binary file.
The process requires a single manual calibration step - in order to find the maximal volume for the speaker, which will not saturate the microphone.

The modem's bitrate is currently 8kbps ([constellation diagram](http://i.imgur.com/JAbGkIt.png)) - so it should have no problem sending a simple transaction in O(second).
Moreover, I am sure it can be optimized by using better modulation, error correction and better audio equipment.

Currently, the documentation is quite lacking, but today was the first time I successfully transmitted 1KB of data between 2 PCs, so I am quite excited :)
The recorded audio file is currently stored at `rx.int16` - and can be demodulated by running:

	$ virtualenv env
	$ source env/bin/activate
	$ pip install reedsolo numpy
	$ python recv.py

I would be happy to continue developing this library, in order to be able to integrate it with popular Bitcoin wallets, to support air-gapped transaction signing.