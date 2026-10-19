import QtQuick 2.15

Image {
    id: root

    property real stage: 0

    source: "images/bg.jpg"
    fillMode: Image.PreserveAspectCrop
    onStageChanged: {
        if (stage == 1)
            introAnimation.running = true;

    }

    Image {
        id: gear
        AnimatedImage{
            id: animation;
            source: "images/pisi.gif"

        }
        width: 100
        height: 100
        transformOrigin: Item.Center

        anchors {
            horizontalCenter: parent.horizontalCenter
            bottom: parent.bottom
            bottomMargin: 50
        }
        
    }


}
