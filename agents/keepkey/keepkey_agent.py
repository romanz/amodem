import libagent.gpg
import libagent.ssh
from libagent.device import keepkey

ssh_agent = lambda: libagent.ssh.main(keepkey.KeepKey)
