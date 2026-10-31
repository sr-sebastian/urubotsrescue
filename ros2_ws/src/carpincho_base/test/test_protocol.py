import struct

from carpincho_base import protocol as p

# Vector de referencia generado por el firmware (firmware/carpincho_base/test_host/test_protocol.cpp)
FW_FRAME_DRIVE = bytes.fromhex("0301070101023f010580be4d0b00")


def test_crc_known_vector():
    assert p.crc16(b"123456789") == 0x29B1


def test_frame_matches_firmware():
    assert p.build_frame(p.CMD_DRIVE, 7, p.drive(0.5, -0.25)) == FW_FRAME_DRIVE


def test_cobs_roundtrip():
    for n in range(0, 300, 7):
        data = bytes((0 if (i * 37) % 5 == 0 else (i * 13) & 0xFF) for i in range(n))
        enc = p.cobs_encode(data)
        assert 0 not in enc
        assert p.cobs_decode(enc) == data


def test_receiver_resync_and_crc():
    rx = p.Receiver()
    junk = b"\x11\x22\x00\x05\x00"
    pkts = rx.feed(junk + FW_FRAME_DRIVE)
    assert len(pkts) == 1
    assert pkts[0].msg_id == p.CMD_DRIVE and pkts[0].seq == 7
    assert struct.unpack("<ff", pkts[0].payload) == (0.5, -0.25)
    bad = bytearray(FW_FRAME_DRIVE)
    bad[3] ^= 0x40
    assert rx.feed(bytes(bad)) == []
    assert rx.crc_errors + rx.framing_errors >= 1


def test_state_parse():
    payload = struct.pack(p.FMT_STATE, 1000, 10, -20, 0.1, -0.1, 0.5, 0.0, 24000, 150, 0x81, 3)
    frame = p.build_frame(p.MSG_STATE, 1, payload)
    (pkt,) = p.Receiver().feed(frame)
    s = p.parse(pkt)
    assert isinstance(s, p.State)
    assert s.batt_mv == 24000 and s.motors_enabled and s.flipper_calibrated
    assert p.fault_names(s.faults) == ["CMD_TIMEOUT", "ESTOP"]


def test_battery_percent_monotonic():
    vals = [p.battery_percent_6s(v / 10) for v in range(190, 260)]
    assert vals[0] == 0 and vals[-1] == 100
    assert all(b >= a for a, b in zip(vals, vals[1:]))
