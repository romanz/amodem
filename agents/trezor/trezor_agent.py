from libagent import signify, gpg, ssh
from libagent.device.trezor import Trezor as DeviceType

ssh_agent = lambda: ssh.main(DeviceType)
gpg_tool = lambda: gpg.main(DeviceType)
gpg_agent = lambda: gpg.run_agent(DeviceType)
signify_tool = lambda: signify.main(DeviceType)
