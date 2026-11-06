import dbus, sys
bus = dbus.SystemBus()
ns = dbus.Interface(bus.get_object('org.bluez', '/org/bluez/hci0'), 'org.bluez.NetworkServer1')
for u in ["nap", "NAP", "00001116-0000-1000-8000-00805f9b34fb",
          "{00001116-0000-1000-8000-00805f9b34fb}",
          "{00001116-0000-1000-8000-00805f9b34fb}".lower()]:
    try:
        ns.Register("pan0", u)
        print("REGISTER OK với uuid =", u)
        sys.exit(0)
    except dbus.DBusException as e:
        print("fail:", u, "->", str(e)[:70])
print("TẤT CẢ FAIL")
sys.exit(1)
