import os
import json
from flask import Flask, redirect, url_for, request, flash
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from flask import render_template

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/sagman/projects/Project-Telegram_bot-web-page/chat_clan.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024 

db = SQLAlchemy(app)

# --- 1. Dynamic Table Reflection ---
with app.app_context():
    db.engine.connect() 
    metadata = MetaData()
    metadata.reflect(bind=db.engine)
    
    reflected_models = {}
    for table_name, table_obj in metadata.tables.items():
        if table_name == 'sqlite_sequence':
            continue
            
        class_name = table_name.capitalize().replace("_", "")
        model_class = type(class_name, (db.Model,), {'__table__': table_obj})
        reflected_models[table_name] = model_class

# --- 2. Custom View for Editing/Uploading JSON Files ---
class JsonAdminView(BaseView):
    def __init__(self, file_path, name, **kwargs):
        self.file_path = file_path
        super(JsonAdminView, self).__init__(name=name, **kwargs)

    @expose('/', methods=['GET', 'POST'])
    def index(self):
        if request.method == 'POST':
            if 'json_file' in request.files and request.files['json_file'].filename != '':
                file = request.files['json_file']
                try:
                    data = json.load(file)
                    with open(self.file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                    flash(f'File uploaded and {self.name} updated!', 'success')
                except Exception as e:
                    flash(f'Upload Error: {str(e)}', 'error')
            
            elif request.form.get('json_data'):
                try:
                    json_dict = json.loads(request.form.get('json_data'))
                    with open(self.file_path, 'w', encoding='utf-8') as f:
                        json.dump(json_dict, f, indent=4, ensure_ascii=False)
                    flash(f'Updated {self.name} via text!', 'success')
                except Exception as e:
                    flash(f'JSON Error: {str(e)}', 'error')

        content = ""
        file_size_mb = 0
        if os.path.exists(self.file_path):
            file_size_mb = os.path.getsize(self.file_path) / (1024 * 1024)
            if file_size_mb < 1.0:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    try:
                        content = json.dumps(json.load(f), indent=4, ensure_ascii=False)
                    except:
                        content = "{}"
            else:
                content = "// File is too large for the text area. Use the Upload feature."
            
        return self.render('admin/json_edit.html', content=content, filename=self.name, size=round(file_size_mb, 2))

# --- 3. Setup Admin Panel ---
admin = Admin(app, name='Clan Project Admin')

# Standard DB views stay in "Database" category
for table_name, model in reflected_models.items():
    view_class = type(f"{table_name}View", (ModelView,), {'column_display_pk': True})
    admin.add_view(view_class(model, db.session, name=f"DB: {table_name}", category="Database"))

# JSON editing views
admin.add_view(JsonAdminView('tanks_data.json', 'Tanks', endpoint='tanks_json', category="JSON Files"))
admin.add_view(JsonAdminView('maps.json', 'Maps', endpoint='maps_json', category="JSON Files"))
admin.add_view(JsonAdminView('combined_data.json', 'Combined', endpoint='combined_json', category="JSON Files"))

@app.route('/')
def home():
    """
    This is the landing page for the project.
    It renders the index.html template.
    """
    return render_template('index.html')

@app.route('/')
def index():
    return redirect(url_for('admin.index'))

if __name__ == '__main__':
    app.run(debug=True, threaded=True)