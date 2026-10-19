import QtQuick 2.15
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.plasma.components 2.0 as PlasmaComponents
import org.kde.plasma.extras 2.0 as PlasmaExtra
import QtQuick.Window 2.15

Item {
    property QtObject rootItem
    height: Math.min(units.gridUnit * 15, Screen.desktopAvailableHeight / 5)
    width: height

    //  /--------------------\
    //  |      spacing       |
    //  | /----------------\ |
    //  | |                | |
    //  | |      icon      | |
    //  | |                | |
    //  | |                | |
    //  | \----------------/ |
    //  |      spacing       |
    //  | [progressbar/text] |
    //  |      spacing       |
    //  \--------------------/

    PlasmaCore.IconItem {
        id: icon

        height: parent.height - progressBar.height - ((units.smallSpacing / 2) * 3) //it's an svg
        width: parent.width

        source: rootItem.icon
    }

    PlasmaComponents.ProgressBar {
        id: progressBar

        anchors {
            bottom: parent.bottom
            left: parent.left
            right: parent.right
            margins: Math.floor(units.smallSpacing / 2)
        }

        visible: rootItem.showingProgress
        minimumValue: 0
        maximumValue: 100

        value: Number(rootItem.osdValue)
    }

    PlasmaExtra.Heading {
        anchors {
            bottom: parent.bottom
            left: parent.left
            right: parent.right
            margins: Math.floor(units.smallSpacing / 2)
        }

        visible: !rootItem.showingProgress
        text: rootItem.showingProgress ? "" : (rootItem.osdValue ? rootItem.osdValue : "")
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.NoWrap
        elide: Text.ElideLeft
        minimumPointSize: theme.defaultFont.pointSize
        fontSizeMode: Text.HorizontalFit
    }
}
