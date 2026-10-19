import QtQuick 2.15
import QtQuick.Window 2.15
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.plasma.components 2.0 as PlasmaComponents
import org.kde.plasma.extras 2.0 as PlasmaExtra

PlasmaCore.Dialog {
    id: root
    location: PlasmaCore.Types.Floating
    type: PlasmaCore.Dialog.OnScreenDisplay
    outputOnly: true

    // OSD Timeout in msecs - how long it will stay on the screen
    property int timeout: 1800
    // This is either a text or a number, if showingProgress is set to true,
    // the number will be used as a value for the progress bar
    property var osdValue
    // Icon name to display
    property string icon
    // Set to true if the value is meant for progress bar,
    // false for displaying the value as normal text
    property bool showingProgress: false

    property bool animateOpacity: false

    Behavior on opacity {
        SequentialAnimation {
            // prevent press and hold from flickering
            PauseAnimation { duration: 100 }
            NumberAnimation {
                duration: root.timeout
                easing.type: Easing.InQuad
            }
        }
        enabled: root.animateOpacity
    }

    mainItem: OsdItem {
        rootItem: root
    }
}
