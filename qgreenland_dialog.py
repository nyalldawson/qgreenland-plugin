# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QGreenlandDialog
                                 A QGIS plugin
 Download QGreenland dataset
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2021-08-17
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Matteo Ghetta (Faunalia)
        email                : matteo.ghetta@faunalia.eu
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import json

from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtWidgets import (
    QFileDialog,
    QSizePolicy,
    QGridLayout
)
from qgis.PyQt.QtCore import QSortFilterProxyModel, QUrl, QModelIndex
from qgis.PyQt.QtGui import QIcon, QStandardItemModel, QStandardItem
from qgis.PyQt.Qt import Qt
from qgis.PyQt.QtNetwork import QNetworkRequest

from qgis.core import (
    QgsApplication,
    Qgis,
    QgsNetworkAccessManager,
    QgsSettings
)

from qgis.gui import (
    QgsMessageBar
)

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgreenland_dialog_base.ui'))



class QGreenlandDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(QGreenlandDialog, self).__init__(parent)
        self.setupUi(self)

        # create a QStandardItemModule
        self.list_model = QStandardItemModel(self)

        # create a QSortFilterProxyModel used to search strings in the Widget
        self.filter_model = QSortFilterProxyModel(self)
        # set the itemModel to the QSortFilterProxyModel
        self.filter_model.setSourceModel(self.list_model)
        self.filter_model.setRecursiveFilteringEnabled(True)
        self.filter_model.setFilterCaseSensitivity(False)

        # set the QStandardItemModel to the treeView
        self.treeView.setModel(self.filter_model)

        # variable to ignore the changes made in the model (cheked or unchecked items)
        self.ignore_model_changes = False

        # create instance of QgsMessageBar and add the widget to the layout
        self.bar = QgsMessageBar()
        self.layout().addWidget(self.bar, 0, 0, -1, 3, Qt.AlignTop)
        # call whenever needed with
        # self.bar.pushMessage(self.tr("Message"), "", level=Qgis.Info, duration=3)

        # connect the Next and Prev buttons to the methods that change the page
        self.next_button.clicked.connect(self._next)
        self.prev_button.clicked.connect(self._prev)

        self.close_button.clicked.connect(self._close)

        # add to the server_list combobox the URLS
        self.server_list_combo.addItem(self.tr('NSIDC: http://qgreenland.apps.nsidc.org/layers/'), 'http://qgreenland.apps.nsidc.org/layers/')
        self.server_list_combo.addItem(self.tr('PGC: https://example.com/qgreenland'), 'https://example.com/qgreenland')

        # pressing (not only selecting or checking) on an item fills the information
        self.treeView.selectionModel().currentChanged.connect(self.display_information)

        self.list_model.itemChanged.connect(self.on_item_changed)
        self.list_model.itemChanged.connect(self.get_checked_items)

        # when the text changes connect to the filter function
        self.search_box.textChanged.connect(self.set_filter_string)

        # connect to the methods that creates the QGreenland folder if not exists
        self._user_profile_folder()

        # fill the treeView with the json information
        self._fill_tree()

        # connect the Download button with the download_data method
        self.download_button.clicked.connect(self.download_data)

        # connect the Browse button to the choose folder method
        self.browse_button.clicked.connect(self.browse_folder)

        # set the download button to not enabled (it will only if a folder has been chosen)
        self.download_button.setEnabled(False)

        # set the close button to not visible at the launch of the plugin
        self.close_button.setVisible(False)

        self.stackedWidget.currentChanged.connect(self.on_page_changed)

        # initialize the QgsSettings
        self.settings = QgsSettings()


    def _user_profile_folder(self):
        """
        check if the user profile folder QGreenland exists and read the local
        file with all the downloaded layer information to match the data version
        """

        self.profile_path = QgsApplication.qgisSettingsDirPath()
        self.qgreenland_path = os.path.join(self.profile_path, 'QGreenland')

        # if not os.path.exists(self.qgreenland_path):
        try:
            os.mkdir(self.qgreenland_path)
        except FileExistsError as e:
            pass

    def on_page_changed(self):
        """
        enable/disable set as visible/not visible the next button depening
        on different conditions
        """

        # get the current page name
        page_name = self.stackedWidget.currentWidget().objectName()

        # get the set of all the checked items (children) pf the QTreeView
        items = self.get_checked_items()

        # hide the next button on the last page
        if page_name == 'download_page':
            self.next_button.setVisible(False)
            self.close_button.setVisible(True)
        else:
            self.next_button.setVisible(True)

        # disable the next button default on the list_page
        if page_name == 'list_page':
            self.next_button.setEnabled(False)
            self.close_button.setVisible(False)
        else:
            self.next_button.setEnabled(True)

        # enable the next button only if there are some checked items in the list
        if items:
            self.next_button.setEnabled(True)


    def _next(self):
        """
        go to the next page of the stacked widget
        """

        # get the current index of the stackedWidget
        i = self.stackedWidget.currentIndex()

        # go to the next page
        self.stackedWidget.setCurrentIndex(i+1)

    def _prev(self):
        """
        go to the previous page of the stacked widget
        """

        # get the current index of the stackedWidget
        i = self.stackedWidget.currentIndex()

        # go to the previous page
        self.stackedWidget.setCurrentIndex(i-1)

    def _close(self):
        """
        close the main dialog window when a signal is fired
        """
        self.close()

    def _download(self):
        """
        go to the download page of the stacked widget
        """

        # get the current index of the stackedWidget
        i = self.stackedWidget.currentIndex()

        # go to the download page
        self.stackedWidget.setCurrentIndex(i+1)

    def _fill_tree(self):
        """
        Fill the treeView with the json file creating QTreeViewItem items
        and parents

        Sets the items as checkable and unchecked by default
        """

        # clear the treeView
        self.list_model.clear()

        # call the read_json function that reads the eventual existing json
        # file with the downloaded information of the files
        if os.path.exists(os.path.join(self.qgreenland_path, 'layers.json')):
            downloaded_layers = self.read_json(os.path.join(self.qgreenland_path, 'layers.json'))

        # temporary read the manifest local json file
        # make it persistent as self.data
        # json_file = os.path.join(os.path.dirname(__file__), 'manifest.json')
        # with open(json_file, 'r') as f:
        #     self.data = json.load(f)

        # load the manifest data from the remote url
        # make it persistent as self.data

        # url = QUrl('http://localhost:8080/manifest.json')
        url = QUrl(self.server_list_combo.currentData() + 'manifest.json')
        network_request = QNetworkRequest(url)
        reply = QgsNetworkAccessManager.instance().blockingGet(network_request)
        reply_content = reply.content()
        self.data = json.loads(reply_content.data().decode())

        # loop into the hierarchies and fill the QTreeView with them
        for layer in self.data['layers']:
            layer_hierarchy = layer['hierarchy']
            parent_item = None

            while layer_hierarchy:
                parent_text = layer_hierarchy[0]
                del layer_hierarchy[0]

                # try to find existing item for this group
                if parent_item:
                    start_index = self.list_model.index(0, 0, self.list_model.indexFromItem(parent_item))
                else:
                    start_index = self.list_model.index(0,0, QModelIndex())
                candidate_indices = self.list_model.match(start_index, Qt.DisplayRole, parent_text, flags=Qt.MatchExactly)

                if not candidate_indices:
                    new_parent_item = QStandardItem(parent_text)
                    new_parent_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
                    new_parent_item.setCheckState(Qt.Unchecked)  # first columun, checkable, checked=0
                    if parent_item:
                        parent_item.appendRow([new_parent_item])
                    else:
                        self.list_model.appendRow([new_parent_item])
                    parent_item = new_parent_item
                else:
                    parent_item = self.list_model.itemFromIndex(candidate_indices[0])

            # create the child (checkable)
            child = QStandardItem(layer['title'])
            # set the custom data for the item as the unique id of each layer
            child.setData(layer['id'], Qt.UserRole)
            child.setFlags(Qt.ItemIsEnabled|Qt.ItemIsSelectable|Qt.ItemIsUserCheckable)
            # to add an icon to the single item
            # child.setIcon(0, QIcon(os.path.join(os.path.dirname(__file__), 'qgreenland-icon.png')))
            child.setCheckState(Qt.Unchecked)

            # add the icons depending on the checksum
            # only if the json file in the profile folder exists
            try:
                for static_layer in downloaded_layers:
                    for i in static_layer['assets']:
                        # check if the layer of the manifest is in the static json file of the profile folder
                        if layer['id'] in static_layer['id']:
                            # get the data type - the layer
                            if i['type'] == 'data':
                                # if the checksum is the same - we have the most recent layer downloaded
                                if layer['assets'][0]['checksum'] == i['checksum']:
                                    child.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons','uptodate.png')))
                                    child.setToolTip(self.tr("You already have the most recent data downloaded"))
                                # if the checksum is not the same - warn the user with the specified icon
                                elif layer['assets'][0]['checksum'] != i['checksum']:
                                    child.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons','outdate.png')))
                                    child.setToolTip(self.tr("A more recent version of the file is available"))
            except:
                pass

            # add the child to the parent item
            parent_item.appendRow([child])

        # sort the tree by the first column and A->Z (should be done at the end to avoid performance issues)
        self.treeView.sortByColumn(0, 0)


    def display_information(self, current, previous):
        """
        Fill the text edit with the information taken from the manifest file
        """

        # get the current item of the treeView
        item = self.list_model.itemFromIndex(self.filter_model.mapToSource(current))

        # only children have parents :)
        if item.parent() is not None:

            # loop into the manifest file (self.data = dictionary)
            for layer in self.data['layers']:

                # get the correspondence between the clicked layer in the treeView and the title in the dictionary
                if layer['title'] == item.text():

                    text = f'''
                    <h2>Name</h2>
                    {layer['title']}
                    <h2>Description</h2>
                    {layer['description']}
                    <h2>Details</h2>
                    {layer['layer_details']}
                    '''

                    self.summary_text.setHtml(text)


    def get_checked_items(self):
        """
        get a list of all the checked items
        to get the unique id for each layer: item.data(Qt.UserRole)
        """

        # get a set to have unique and not repeated data that belongs to different categories
        checked_items = set()

        # loop in the model and list all the items
        for item in self.list_model.findItems("", Qt.MatchContains | Qt.MatchRecursive):
            # get only the checked items
            if item.checkState() == Qt.Checked:
                # add to the set the Qt.UserRole (AKA label) defined above
                checked_items.add(item.data(Qt.UserRole))

        # enable the next button if there are some chosen items in the list
        if not checked_items:
            self.next_button.setEnabled(False)
        else:
            self.next_button.setEnabled(True)

        return checked_items


    def write_json(self, item_list):
        """
        method to call when downloading the selected files. Writes a json file
        in the QGreenland folder within the QGIS profile one with the layer
        information that we need. The json is a list of single layers, where each
        layer has the following structure:

        {
            "id": "nunagis_polar_bears",
            "assets": [
                {
                    "file": "nunagis_bears.gpkg",
                    "type": "data",
                    "checksum": "ff68078f6ef14df085c2d84e2eff573e",
                    "size_bytes": 184320
                },
                {
                    "file": "nunagis_bears.qml",
                    "type": "style",
                    "checksum": "ksc14ec6110fa820ca6b65f5aec85911",
                    "size_bytes": 1521
                },
                {
                    "file": "nunagis_bears.xml",
                    "type": "ancillary",
                    "checksum": "po91b6919b9a77a9fe98a8e574214abf",
                    "size_bytes": 2091
                }
            ]
        },

        We will use the checksum parameter to check if the layer downloaded is
        outdated (has a different checksum) and warn the user.

        :param item_list: set of checked layers in the treeView
        :type item_list: set
        """

        # empty list that will be filled
        downloaded_layers = []

        # check if a json file already exists adn overwrite the existing list
        if os.path.exists(os.path.join(self.qgreenland_path, 'layers.json')):
            downloaded_layers = self.read_json(os.path.join(self.qgreenland_path, 'layers.json'))

        # get a set of the existing layer id of the json file to avoid appending the same value
        layers_in_json = set()
        for lay in downloaded_layers:
            layers_in_json.add(lay['id'])


        # loop in the item list and check if the id of the selected layer is already in the file
        for item in item_list:
            # temporary dictionary that will be filled with the layer information
            d = {}

            for layer in self.data['layers']:
                # check if the if of the whole layer list is both a checked item
                # and is not in the set
                if layer['id'] == item and layer['id'] not in layers_in_json:

                    # add to the dictionray the information needed
                    d['id'] = layer['id']
                    d['assets'] = layer['assets']

                    # append to the list the dictionary for every item
                    downloaded_layers.append(d)

        # write the final json file with the updated list
        with open(os.path.join(self.qgreenland_path, 'layers.json'), 'w') as json_file:
            json.dump(downloaded_layers, json_file, indent=4)


    def read_json(self, json_path):
        """
        given a path of the json file, read and return it as a list

        :param json_path: path of the json file
        :type json_path: str
        :return: dump of the json file
        :rtype: list
        """

        with open(json_path, 'r') as json_file:
            downloaded_layers = json.load(json_file)

        return downloaded_layers


    def set_filter_string(self):
        """
        method to filter the treeView according to the string entered
        """

        # get the text of the search_box
        filter_string = self.search_box.text()

        # if any text
        if filter_string:
            # filter with a wildcard before and after the string
            self.filter_model.setFilterWildcard('*' + filter_string + '*')
            self.treeView.expandAll()
        else:
            self.filter_model.setFilterWildcard('')
            self.treeView.collapseAll()


    def on_item_changed(self, item):
        """
        method to set the parent checked or partially checked depending on the
        children state

        :param item: QTreeViewItem
        :type item: QTreeViewItem
        """

        # if nothing is made just return
        if self.ignore_model_changes:
            return

        # it the child is partially checked just return
        if item.checkState() == Qt.PartiallyChecked:
            return

        # set the initial variable to True because something has been made
        self.ignore_model_changes = True

        # if the parent is checked all the children have to be checked as well
        # loop into the row count of the item (that is the parent)
        for row in range(item.rowCount()):
            # get the child
            child = item.child(row)
            # set the child state as the parent one
            child.setCheckState(item.checkState())

        # if the parent is checked all the children have to be checked as well
        # loop into the row count of the item (that is the parent)
        def check_recursive(item, check_state):
            item.setCheckState(check_state)
            for row in range(item.rowCount()):
                # get the child
                check_recursive(item.child(row), check_state)

        for row in range(item.rowCount()):
            check_recursive(item.child(row), item.checkState())

        # get the check state of the children of the corresponding parent -- we need to do this recursively
        def set_parent_check_state(parent):
            # test if all the parent's children are checked or unchecked or mixed state
            children_check_state = [parent.child(row).checkState() for row in range(parent.rowCount())]
            # if all the children are checked then set to checked also the parent
            if all(state == Qt.Checked for state in children_check_state):
                parent.setCheckState(Qt.Checked)
            # if all the children are unchecked set to uncheck also the parent
            elif all(state == Qt.Unchecked for state in children_check_state):
                parent.setCheckState(Qt.Unchecked)
            # if just some of the children are checked set the parent as partially checked
            else:
                parent.setCheckState(Qt.PartiallyChecked)

            if parent.parent():
                set_parent_check_state(parent.parent())

        if item.parent():
            set_parent_check_state(item.parent())

        # set the variable to false again to reset the behavior
        self.ignore_model_changes = False

    def download_data(self):
        """
        method that downloads all the selected data (AKA checked items)
        """

        # that's the list (or set) of the data to download
        items = self.get_checked_items()
        if items:
            self.write_json(items)

        # get the dictionary of all the layer to be downloaded with key=folder and value=layer name
        layer_to_download = {}
        for layer in self.data['layers']:
            for current, parent in enumerate(items):
                if layer['id'] == parent:
                    layer_to_download[parent] = layer['assets'][0]['file']

        # just get the length of the list divided by 100
        total = 100 / len(layer_to_download)

        # clear the download label text
        self.download_label.setText("")

        # loop on the dictionary of layers and move the progress bar
        for current, (parent, item) in enumerate(layer_to_download.items()):

            self.download_label.setText(f"Downloading {item} {current + 1} of {len(layer_to_download)}")
            self.progressBar.setValue(int((current + 1) * total))

            # if we have data (default links have been chosen) then get the url from the data
            # if a custom url has been entered get the text else get the text
            if self.server_list_combo.currentData():
                downloading_url = self.server_list_combo.currentData()
            else:
                downloading_url = self.server_list_combo.currentText()

            # just for now
            # downloading_url = 'http://localhost:8080/'

            downloading_url = downloading_url + '/' + parent + '/' + item

            # create a network request and the corresponding reply object
            url = QUrl(downloading_url)
            network_request = QNetworkRequest(url)
            reply = QgsNetworkAccessManager.instance().blockingGet(network_request)
            reply_content = reply.content()

            # create the path to where to save the file
            saving_path = os.path.join(self.saving_folder, item)

            # write the reply to a file
            with open(saving_path, 'wb') as f:
                f.write(reply_content)


    def browse_folder(self):
        """
        open a QDialog to choose the folder where to save the data
        """

        # get the saving_path chosen: return None if empty
        saving_path = self.settings.value("qgreenland-plugin-saving_folder")

        self.saving_folder = QFileDialog.getExistingDirectory(
            None,
            self.tr("Choose a directory to save the data"),
            saving_path,
            QFileDialog.ShowDirsOnly
        )

        # remember the last folder chosen
        self.settings.setValue("qgreenland-plugin-saving_folder", self.saving_folder)

        if not self.saving_folder:
            self.bar.pushMessage(self.tr("You have to select a folder where to save the data"), "", level=Qgis.Critical, duration=-1)
            return
        else:
            self.download_button.setEnabled(True)

        self.folder_path.setText(self.saving_folder)