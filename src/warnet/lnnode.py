import json
import os
from warnet.utils import exponential_backoff, generate_ipv4_addr
from backends import BackendInterface, ServiceType
from .status import RunningStatus
from typing import List


class LNNode:
    def __init__(self, warnet, tank, impl, backend: BackendInterface):
        self.warnet = warnet
        self.tank = tank
        assert impl == "lnd"
        self.impl = impl
        self.backend = backend
        self.ipv4 = generate_ipv4_addr(self.warnet.subnet)
        self.rpc_port = 10009

    @property
    def status(self) -> RunningStatus:
        return self.warnet.container_interface.get_status(self.tank.index, ServiceType.LIGHTNING)

    @exponential_backoff(max_retries=20, max_delay=300)
    def lncli(self, cmd) -> str:
        cmd = f"lncli --network=regtest {cmd}"
        return self.backend.exec_run(self.tank.index, ServiceType.LIGHTNING, cmd)

    def getnewaddress(self):
        res = json.loads(self.lncli("newaddress p2wkh"))
        return res["address"]

    def getURI(self):
        res = json.loads(self.lncli("getinfo"))
        return res["uris"][0]

    def open_channel_to_tank(self, index, amt):
        tank = self.warnet.tanks[index]
        [pubkey, host] = tank.lnnode.getURI().split("@")
        res = json.loads(
            self.lncli(f"openchannel --node_key={pubkey} --connect={host} --local_amt={amt}")
        )
        return res

    def connect_to_tank(self, index):
        tank = self.warnet.tanks[index]
        uri = tank.lnnode.getURI()
        res = self.lncli(f"connect {uri}")
        return res

    def generate_cli_command(self, command: List[str]):
        network = f"--network={self.tank.warnet.bitcoin_network}"
        cmd = f"{network} {' '.join(command)}"
        match self.impl:
            case "lnd":
                cmd = f"lncli {cmd}"
            case "cln":
                cmd = f"lightning-cli {cmd}"
            case _:
                raise Exception(f"Unsupported LN implementation: {self.impl}")
        return cmd

    def export(self, config, subdir):
        container_name = self.backend.get_container_name(self.tank.index, ServiceType.LIGHTNING)
        macaroon_filename = f"{container_name}_admin.macaroon"
        cert_filename = f"{container_name}_tls.cert"
        macaroon_path = os.path.join(subdir, macaroon_filename)
        cert_path = os.path.join(subdir, cert_filename)
        macaroon = self.backend.get_file(
            self.tank.index,
            ServiceType.LIGHTNING,
            "/root/.lnd/data/chain/bitcoin/regtest/admin.macaroon",
        )
        cert = self.backend.get_file(self.tank.index, ServiceType.LIGHTNING, "/root/.lnd/tls.cert")

        with open(macaroon_path, "wb") as f:
            f.write(macaroon)

        with open(cert_path, "wb") as f:
            f.write(cert)

        config["nodes"].append(
            {
                "id": container_name,
                "address": f"https://{self.ipv4}:{self.rpc_port}",
                "macaroon": macaroon_path,
                "cert": cert_path,
            }
        )
