import libagent.gpg
import libagent.ssh
from libagent.device.ledger import LedgerNanoS as DeviceType

ssh_agent = lambda: libagent.ssh.main(DeviceType)
gpg_tool = lambda: libagent.gpg.main(DeviceType)
gpg_agent = lambda: libagent.gpg.run_agent(DeviceType)
