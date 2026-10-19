import QtQuick 2.15
import QtQuick.Layouts 1.3
import QtQuick.Window 2.15
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.plasma.components 2.0 as PlasmaComponents
import org.kde.plasma.extras 2.0 as PlasmaExtras
import org.kde.milou 0.1 as Milou

ColumnLayout {
    id: root
    property string query
    property string runner
    property bool showHistory: false

    onQueryChanged: {
        queryField.text = query;
    }

    Connections {
        target: runnerWindow
        onVisibleChanged: {
            if (runnerWindow.visible) {
                queryField.forceActiveFocus();
                listView.currentIndex = -1;
            } else {
                root.query = "";
                root.runner = "";
                root.showHistory = false;
            }
        }
    }

    RowLayout {
        Layout.alignment: Qt.AlignTop
        PlasmaComponents.ToolButton {
            iconSource: "configure"
            onClicked: {
                runnerWindow.visible = false;
                runnerWindow.displayConfiguration();
            }
            Accessible.name: i18nd("plasma_lookandfeel_org.kde.lookandfeel", "Configure")
            Accessible.description: i18nd("plasma_lookandfeel_org.kde.lookandfeel", "Configure Search Plugins")
        }
        PlasmaComponents.TextField {
            id: queryField
            property bool allowCompletion: false

            clearButtonShown: true
            Layout.minimumWidth: units.gridUnit * 25

            activeFocusOnPress: true
            placeholderText: results.runnerName ? i18ndc("plasma_lookandfeel_org.kde.lookandfeel",
                                                         "Textfield placeholder text, query specific KRunner",
                                                         "Search '%1'...", results.runnerName)
                                                : i18ndc("plasma_lookandfeel_org.kde.lookandfeel",
                                                         "Textfield placeholder text", "Search...")

            onTextChanged: {
                root.query = queryField.text;
                if (allowCompletion && length > 0) {
                    var history = runnerWindow.history;

                    for (var i = 0, j = history.length; i < j; ++i) {
                        var item = history[i];

                        if (item.toLowerCase().indexOf(text.toLowerCase()) === 0) {
                            var oldText = text;
                            text = text + item.substr(oldText.length);
                            select(text.length, oldText.length);
                            break;
                        }
                    }
                }
            }

            Keys.onPressed: allowCompletion = (event.key !== Qt.Key_Backspace && event.key !== Qt.Key_Delete);
            Keys.onUpPressed: {
                if (length === 0) {
                    root.showHistory = true;
                }
            }
            Keys.onDownPressed: {
                if (length === 0) {
                    root.showHistory = true;
                }
            }

            Keys.onEscapePressed: {
                runnerWindow.visible = false;
            }
            Keys.forwardTo: [listView, results];
        }
        PlasmaComponents.ToolButton {
            iconSource: "window-close"
            onClicked: runnerWindow.visible = false;
            Accessible.name: i18nd("plasma_lookandfeel_org.kde.lookandfeel", "Close")
            Accessible.description: i18nd("plasma_lookandfeel_org.kde.lookandfeel", "Close Search")
        }
    }

    PlasmaExtras.ScrollArea {
        Layout.alignment: Qt.AlignTop
        visible: results.count > 0
        enabled: visible
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(Screen.height, results.contentHeight)

        Milou.ResultsView {
            id: results
            queryString: root.query
            runner: root.runner

            onActivated: {
                runnerWindow.addToHistory(queryString);
                runnerWindow.visible = false;
            }

            onUpdateQueryString: {
                queryField.text = text;
                queryField.cursorPosition = cursorPosition;
            }
        }
    }

    PlasmaExtras.ScrollArea {
        Layout.alignment: Qt.AlignTop
        Layout.fillWidth: true
        visible: root.query.length === 0 && listView.count > 0
        enabled: visible
        Layout.preferredHeight: Math.min(Screen.height, listView.contentHeight)

        ListView {
            id: listView
            keyNavigationWraps: true
            highlight: PlasmaComponents.Highlight {}
            highlightMoveDuration: 0
            model: root.showHistory ? runnerWindow.history.slice(0, 20) : []
            delegate: Milou.ResultDelegate {
                id: resultDelegate
                width: listView.width
                typeText: index === 0 ? i18nd("plasma_lookandfeel_org.kde.lookandfeel", "Recent Queries") : "";
            }

            Keys.onReturnPressed: runCurrentIndex();
            Keys.onEnterPressed: runCurrentIndex();

            Keys.onTabPressed: incrementCurrentIndex();
            Keys.onBacktabPressed: decrementCurrentIndex();
            Keys.onUpPressed: decrementCurrentIndex();
            Keys.onDownPressed: incrementCurrentIndex();

            function runCurrentIndex() {
                queryField.text = runnerWindow.history[currentIndex];
            }
        }
    }
}
