import os

from flask import url_for, current_app

def add_dataset_name(data_upload,username):

    filename = data_upload.filename
    # Grab extension type
    ext_type = filename.split('.')[-1]
    storage_filename = str(username) + '.' +ext_type

    filepath = os.path.join(current_app.root_path, 'static\pdatasets', storage_filename)
    data_upload.save(filepath)
    return storage_filename
