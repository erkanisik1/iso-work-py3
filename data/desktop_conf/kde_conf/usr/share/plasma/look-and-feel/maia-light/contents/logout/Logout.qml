import QtQuick 2.15 

Item {
    id: root
    height: units.largeSpacing * 14
    width: screenGeometry.width

    signal logoutRequested()
    signal haltRequested()
    signal suspendRequested(int spdMethod)
    signal rebootRequested()
    signal rebootRequested2(int opt)
    signal cancelRequested()
    signal lockScreenRequested()

    LogoutScreen {
        anchors.fill: parent

        mode: switch (sdtype) {
            case ShutdownType.ShutdownTypeNone:
                return "logout";
            case ShutdownType.ShutdownTypeHalt:
                return maysd ? "shutdown" : "logout";
            case ShutdownType.ShutdownTypeReboot:
                return maysd ? "reboot" : "logout";
            default:
                return "logout";
        }

        onShutdownRequested: {
            root.haltRequested()
        }

        onRebootRequested: {
            root.rebootRequested()
        }
        canShutdown: maysd && choose
        canReboot: maysd && choose
        canLogout: true

        onCancel: root.cancelRequested()
    }
}
