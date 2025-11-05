# QGIS Plugin Integration Guide - Metadata Edit API

## Overview

This guide shows how to integrate the new Metadata Edit API into your QGIS plugin, allowing users to edit dataset metadata **after** successful upload.

## Integration Steps

### Step 1: Add "Edit Metadata" Button to Upload Success Dialog

After a successful upload, show an option to edit metadata.

```python
# In your upload success handler
def on_upload_success(self, upload_response):
    """Called when dataset upload completes successfully"""

    dataset_id = upload_response.get('dataset_id')
    dataset_name = upload_response.get('dataset_name', 'Unknown')

    # Show success message with Edit Metadata button
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle("Upload Successful")
    msg_box.setText(f"Dataset '{dataset_name}' uploaded successfully!")
    msg_box.setInformativeText("Would you like to edit metadata now?")

    # Add buttons
    edit_button = msg_box.addButton("Edit Metadata", QMessageBox.AcceptRole)
    later_button = msg_box.addButton("Later", QMessageBox.RejectRole)

    msg_box.exec_()

    if msg_box.clickedButton() == edit_button:
        self.open_metadata_editor(dataset_id)
```

### Step 2: Create Metadata Edit Dialog

Create a dialog for editing metadata fields.

```python
# metadata_editor_dialog.py
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'metadata_editor.ui'))

class MetadataEditorDialog(QDialog, FORM_CLASS):
    """Dialog for editing dataset metadata"""

    def __init__(self, dataset_id, api_client, parent=None):
        super(MetadataEditorDialog, self).__init__(parent)
        self.setupUi(self)

        self.dataset_id = dataset_id
        self.api_client = api_client

        # Connect buttons
        self.buttonBox.accepted.connect(self.save_metadata)
        self.buttonBox.rejected.connect(self.reject)

        # Load current metadata to pre-fill fields
        self.load_metadata()

    def load_metadata(self):
        """Load current metadata from API and pre-fill form"""
        try:
            metadata = self.api_client.get_metadata(self.dataset_id)

            if metadata:
                # Pre-fill form fields
                self.titleLineEdit.setText(metadata.get('title', ''))
                self.descriptionTextEdit.setPlainText(metadata.get('description', ''))

                # Keywords
                keywords = metadata.get('keywords', [])
                self.keywordsLineEdit.setText(', '.join(keywords))

                # Labels (Vietnamese categories)
                labels = metadata.get('labels', [])
                if labels:
                    self.labelsComboBox.setCurrentText(labels[0])

                # Regions
                regions = metadata.get('regions', [])
                self.regionsLineEdit.setText(', '.join(regions))

        except Exception as e:
            QMessageBox.warning(
                self,
                "Load Error",
                f"Failed to load metadata: {str(e)}"
            )

    def save_metadata(self):
        """Save metadata via API"""
        try:
            # Collect form data
            metadata = {
                'title': self.titleLineEdit.text().strip(),
                'description': self.descriptionTextEdit.toPlainText().strip(),
                'keywords': [k.strip() for k in self.keywordsLineEdit.text().split(',') if k.strip()],
                'labels': [self.labelsComboBox.currentText()] if self.labelsComboBox.currentText() else [],
                'regions': [r.strip() for r in self.regionsLineEdit.text().split(',') if r.strip()]
            }

            # Send to API
            result = self.api_client.update_metadata(self.dataset_id, metadata)

            if result and result.get('success'):
                QMessageBox.information(
                    self,
                    "Success",
                    "Metadata updated successfully!"
                )
                self.accept()
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'Unknown error'
                QMessageBox.warning(
                    self,
                    "Update Failed",
                    f"Failed to update metadata: {error_msg}"
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error saving metadata: {str(e)}"
            )
```

### Step 3: Create metadata_editor.ui

Create a Qt Designer UI file with the following fields:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MetadataEditorDialog</class>
 <widget class="QDialog" name="MetadataEditorDialog">
  <property name="windowTitle">
   <string>Edit Dataset Metadata</string>
  </property>
  <layout class="QVBoxLayout">
   <!-- Title -->
   <item>
    <widget class="QLabel">
     <property name="text">
      <string>Title:</string>
     </property>
    </widget>
   </item>
   <item>
    <widget class="QLineEdit" name="titleLineEdit"/>
   </item>

   <!-- Description -->
   <item>
    <widget class="QLabel">
     <property name="text">
      <string>Description:</string>
     </property>
    </widget>
   </item>
   <item>
    <widget class="QTextEdit" name="descriptionTextEdit"/>
   </item>

   <!-- Keywords -->
   <item>
    <widget class="QLabel">
     <property name="text">
      <string>Keywords (comma-separated):</string>
     </property>
    </widget>
   </item>
   <item>
    <widget class="QLineEdit" name="keywordsLineEdit"/>
   </item>

   <!-- Labels -->
   <item>
    <widget class="QLabel">
     <property name="text">
      <string>Category:</string>
     </property>
    </widget>
   </item>
   <item>
    <widget class="QComboBox" name="labelsComboBox">
     <item><property name="text"><string></string></property></item>
     <item><property name="text"><string>Thuỷ lợi</string></property></item>
     <item><property name="text"><string>Bản đồ nền</string></property></item>
     <item><property name="text"><string>Khí tượng thuỷ văn</string></property></item>
     <item><property name="text"><string>Viễn thám</string></property></item>
    </widget>
   </item>

   <!-- Regions -->
   <item>
    <widget class="QLabel">
     <property name="text">
      <string>Regions (comma-separated):</string>
     </property>
    </widget>
   </item>
   <item>
    <widget class="QLineEdit" name="regionsLineEdit"/>
   </item>

   <!-- Buttons -->
   <item>
    <widget class="QDialogButtonBox" name="buttonBox">
     <property name="standardButtons">
      <set>QDialogButtonBox::Cancel|QDialogButtonBox::Save</set>
     </property>
    </widget>
   </item>
  </layout>
 </widget>
</ui>
```

### Step 4: Add API Client Methods

Add methods to your API client for metadata operations.

```python
# api_client.py
import requests
import logging

logger = logging.getLogger(__name__)

class GeoNodeAPIClient:
    """API client for GeoNode metadata operations"""

    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    def get_metadata(self, dataset_id):
        """
        Get metadata for a dataset.

        Args:
            dataset_id (int): Dataset ID

        Returns:
            dict: Metadata dictionary or None if failed
        """
        url = f"{self.base_url}/api/v2/datasets/{dataset_id}/metadata_fields/"

        try:
            logger.info(f"GET {url}")
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"GET metadata failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.exception(f"Error getting metadata: {e}")
            return None

    def update_metadata(self, dataset_id, metadata):
        """
        Update metadata for a dataset.

        Args:
            dataset_id (int): Dataset ID
            metadata (dict): Metadata to update
                {
                    'title': str,
                    'description': str,
                    'keywords': list,
                    'labels': list,
                    'regions': list
                }

        Returns:
            dict: Response dictionary or None if failed
        """
        url = f"{self.base_url}/api/v2/datasets/{dataset_id}/metadata_fields/"

        try:
            logger.info(f"PATCH {url}")
            logger.debug(f"Payload: {metadata}")

            response = requests.patch(
                url,
                headers=self.headers,
                json=metadata,
                timeout=15
            )

            if response.status_code == 200:
                logger.info(f"Metadata updated successfully for dataset {dataset_id}")
                return response.json()
            else:
                logger.error(f"PATCH metadata failed: {response.status_code} - {response.text}")
                return {'error': response.text}

        except Exception as e:
            logger.exception(f"Error updating metadata: {e}")
            return {'error': str(e)}

    def get_datasets(self):
        """
        Get list of datasets (for refreshing Data Source table).

        Returns:
            list: List of datasets or None if failed
        """
        url = f"{self.base_url}/api/v2/datasets/"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get('datasets', [])
            else:
                logger.error(f"GET datasets failed: {response.status_code}")
                return None

        except Exception as e:
            logger.exception(f"Error getting datasets: {e}")
            return None
```

### Step 5: Integrate into Main Plugin

Add the metadata editor to your main plugin class.

```python
# main_plugin.py
from .metadata_editor_dialog import MetadataEditorDialog
from .api_client import GeoNodeAPIClient

class YourPlugin:
    """Main plugin class"""

    def __init__(self, iface):
        self.iface = iface
        self.api_client = None

    def initGui(self):
        """Initialize plugin UI"""
        # ... existing code ...

        # Initialize API client
        base_url = self.settings.value('geonode_url', 'http://localhost:8000')
        token = self.settings.value('bearer_token', '')
        self.api_client = GeoNodeAPIClient(base_url, token)

    def open_metadata_editor(self, dataset_id):
        """Open metadata editor dialog"""
        dialog = MetadataEditorDialog(dataset_id, self.api_client, self.iface.mainWindow())

        # Show dialog
        result = dialog.exec_()

        if result == QtWidgets.QDialog.Accepted:
            # Metadata was updated - refresh Data Source table
            self.refresh_datasets_table()

    def refresh_datasets_table(self):
        """Refresh the Data Source table after metadata update"""
        try:
            datasets = self.api_client.get_datasets()

            if datasets:
                # Update your table widget
                self.populate_datasets_table(datasets)

                # Show success message
                self.iface.messageBar().pushMessage(
                    "Success",
                    "Dataset list refreshed",
                    level=Qgis.Success,
                    duration=3
                )
        except Exception as e:
            logger.exception(f"Error refreshing datasets: {e}")
            self.iface.messageBar().pushMessage(
                "Error",
                f"Failed to refresh datasets: {str(e)}",
                level=Qgis.Critical
            )
```

### Step 6: Add Context Menu to Datasets Table

Allow users to right-click on a dataset in the Data Source table to edit metadata.

```python
def setup_datasets_table_context_menu(self):
    """Setup context menu for datasets table"""
    self.datasetsTable.setContextMenuPolicy(Qt.CustomContextMenu)
    self.datasetsTable.customContextMenuRequested.connect(
        self.show_datasets_context_menu
    )

def show_datasets_context_menu(self, position):
    """Show context menu for dataset table"""
    menu = QMenu()

    # Get selected dataset
    row = self.datasetsTable.rowAt(position.y())
    if row < 0:
        return

    # Get dataset ID from table
    dataset_id_item = self.datasetsTable.item(row, 0)  # Assuming ID is in column 0
    if not dataset_id_item:
        return

    dataset_id = int(dataset_id_item.text())

    # Add "Edit Metadata" action
    edit_action = menu.addAction("Edit Metadata")
    edit_action.triggered.connect(lambda: self.open_metadata_editor(dataset_id))

    # Add "Refresh" action
    refresh_action = menu.addAction("Refresh")
    refresh_action.triggered.connect(self.refresh_datasets_table)

    # Show menu
    menu.exec_(self.datasetsTable.viewport().mapToGlobal(position))
```

## Complete Workflow Example

Here's the complete workflow from upload to metadata editing:

```python
class CompleteWorkflowExample:
    """Complete example of upload → edit metadata → refresh"""

    def upload_and_edit_workflow(self, file_path):
        """Complete workflow example"""

        # Step 1: Upload dataset
        print("Step 1: Uploading dataset...")
        upload_response = self.upload_dataset(file_path)

        if not upload_response.get('success'):
            print("Upload failed!")
            return

        dataset_id = upload_response['dataset_id']
        print(f"✓ Upload successful! Dataset ID: {dataset_id}")

        # Step 2: Ask user if they want to edit metadata
        reply = QMessageBox.question(
            None,
            "Upload Successful",
            "Would you like to edit metadata now?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.No:
            print("User skipped metadata editing")
            return

        # Step 3: Open metadata editor (pre-filled with current data)
        print("Step 3: Opening metadata editor...")
        dialog = MetadataEditorDialog(dataset_id, self.api_client)

        if dialog.exec_() == QDialog.Accepted:
            print("✓ Metadata saved!")

            # Step 4: Refresh datasets table to show updated metadata
            print("Step 4: Refreshing dataset list...")
            self.refresh_datasets_table()

            print("✓ Complete! Metadata is now visible in Data Source table")
        else:
            print("User cancelled metadata editing")

    def upload_dataset(self, file_path):
        """Upload dataset (existing upload code)"""
        # ... your existing upload code ...
        return {'success': True, 'dataset_id': 123}

    def refresh_datasets_table(self):
        """Refresh datasets table (existing code)"""
        # ... your existing refresh code ...
        pass
```

## Error Handling

Add robust error handling for API calls:

```python
def safe_api_call(self, operation, *args, **kwargs):
    """Wrapper for safe API calls with error handling"""
    try:
        result = operation(*args, **kwargs)

        if result is None:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "API Error",
                "No response from server. Please check your connection."
            )
            return None

        if isinstance(result, dict) and 'error' in result:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "API Error",
                f"Error: {result['error']}"
            )
            return None

        return result

    except requests.exceptions.ConnectionError:
        QMessageBox.critical(
            self.iface.mainWindow(),
            "Connection Error",
            "Cannot connect to GeoNode server. Please check the URL and your network."
        )
        return None

    except requests.exceptions.Timeout:
        QMessageBox.warning(
            self.iface.mainWindow(),
            "Timeout",
            "Request timed out. The server may be slow or unavailable."
        )
        return None

    except Exception as e:
        logger.exception(f"Unexpected error in API call: {e}")
        QMessageBox.critical(
            self.iface.mainWindow(),
            "Unexpected Error",
            f"An unexpected error occurred: {str(e)}"
        )
        return None
```

## Testing Checklist

- [ ] Upload a dataset without metadata
- [ ] Click "Edit Metadata" button after upload
- [ ] Verify metadata editor opens with empty/default fields
- [ ] Fill in title, description, keywords, labels
- [ ] Click "Save"
- [ ] Verify success message appears
- [ ] Verify Data Source table refreshes automatically
- [ ] Verify new metadata appears in table (description, keywords, labels columns)
- [ ] Right-click on dataset in table
- [ ] Select "Edit Metadata" from context menu
- [ ] Verify metadata editor opens with previously saved data
- [ ] Modify some fields and save again
- [ ] Verify table updates with new values

## Benefits Over Old Approach

| Feature | Old Approach | New Approach |
|---------|--------------|--------------|
| **Reliability** | ❌ Often failed due to cache issues | ✅ Direct DB update via API |
| **User Control** | ❌ Automatic (no user visibility) | ✅ Explicit user action |
| **Debugging** | ❌ Required log access | ✅ Clear success/error messages |
| **Edit Later** | ❌ Only during upload | ✅ Anytime after upload |
| **Pre-fill** | ❌ Not possible | ✅ GET current metadata first |
| **Testability** | ❌ Complex (middleware + signals) | ✅ Simple API endpoint tests |

## Migration Guide

If you have existing plugin code using the old upload-time metadata approach:

### Before (Remove this):
```python
# OLD: Sending metadata with upload
upload_data = {
    'base_file': file,
    'dataset_title': title,  # ❌ Remove
    'description': description,  # ❌ Remove
    'keywords': keywords,  # ❌ Remove
    'labels': labels  # ❌ Remove
}
```

### After (Use this):
```python
# NEW: Upload first, edit metadata after
# 1. Upload without metadata
upload_response = upload_dataset(file)
dataset_id = upload_response['dataset_id']

# 2. Edit metadata after upload
if ask_user_to_edit_metadata():
    open_metadata_editor(dataset_id)
```

## FAQ

**Q: Can I still send metadata during upload?**
A: Technically yes, but it won't be saved. The new approach requires editing after upload.

**Q: What if user doesn't want to edit metadata?**
A: That's fine! They can edit it later by right-clicking the dataset in the table.

**Q: Will old datasets work with the new API?**
A: Yes! The GET/PATCH endpoints work with any existing dataset.

**Q: How do I refresh the table after editing?**
A: Call `api_client.get_datasets()` and repopulate your table widget.

---

## Support

For issues or questions:
- Check server logs: `docker-compose logs -f django`
- Check API documentation: `/METADATA_API_DOCUMENTATION.md`
- Test with cURL first before implementing in plugin
- Report issues with full error messages and request/response payloads
