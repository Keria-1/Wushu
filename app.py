from flask import Flask, jsonify, request, send_file, send_from_directory, session, redirect, url_for
from functools import wraps
import os
import re
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

# 初始化Flask应用
app = Flask(__name__,
            static_folder='.',
            static_url_path='')
app.secret_key = 'wushu_study_admin_2026'

# 配置静态文件夹
@app.route('/uploads/avatar/<filename>')
def serve_avatar(filename):
    return send_from_directory('uploads/avatar', filename)

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = 'http://127.0.0.1:5000'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response

# ---------------------- 用户登录校验装饰器----------------------
def user_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return redirect('/login.html')
        return f(*args, **kwargs)
    return decorated

# ---------------------- 头像上传----------------------
@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    user_id = request.form.get('user_id')
    if not user_id:
        return jsonify({"code":400,"msg":"缺少用户ID"})

    if 'avatar' in request.files:
        file = request.files['avatar']
        if file.filename != '':
            upload_folder = 'uploads/avatar'
            os.makedirs(upload_folder, exist_ok=True)

            ext = os.path.splitext(file.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(upload_folder, filename)
            file.save(save_path)

            # 存入数据库的路径
            avatar_path = f"uploads/avatar/{filename}"

            # 保存到数据库
            db = get_db_connection()
            if not db:
                return jsonify({"code":500,"msg":"数据库连接失败"})
            cursor = db.cursor()
            try:
                cursor.execute("""
                    UPDATE ws_user
                    SET avatar = %s, update_time = NOW()
                    WHERE id = %s
                """, (avatar_path, user_id))
                db.commit()
            except Exception as e:
                db.rollback()
                return jsonify({"code":500,"msg":"头像保存失败"})
            finally:
                cursor.close()
                db.close()

            return jsonify({"code":200,"msg":"头像上传成功","avatar":avatar_path})

    return jsonify({"code":400,"msg":"未上传头像"})

# ---------------------- 核心工具函数 ----------------------
# 1. 数据库连接工具函数
def get_db_connection():
    try:
        db = pymysql.connect(
            host='localhost',
            user='root',
            password='Keria..260207',
            database='wushu_study',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return db
    except Exception as e:
        print(f"数据库连接失败：{str(e)}")
        return None

# 2. 管理员登录校验装饰器
def admin_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        admin_id = session.get('admin_id')
        if not admin_id:
            if request.path.startswith('/admin/api/'):
                return jsonify({"code": 401, "msg": "请先登录管理员账号"})
            else:
                return redirect('/admin/login.html')
        return f(*args, **kwargs)
    return decorated

# 3. 快捷生成密码哈希
def generate_admin_pwd(password):
    return generate_password_hash(password, method='pbkdf2:sha256')

# ---------------------- 核心业务接口 ----------------------
# 首页接口
@app.route('/api/index', methods=['GET'])
def get_index_data():
    db = get_db_connection()
    if not db:
        return jsonify({"code": 500, "msg": "数据库连接失败", "data": {}})

    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT id, title, `desc`, image_url as image
            FROM ws_carousel
            WHERE status = 1
            ORDER BY sort ASC
        """)
        carousel_data = cursor.fetchall()

        cursor.execute("""
            SELECT id, title, `desc`, image_url as image
            FROM ws_research
            WHERE status = 1
            ORDER BY sort ASC
            LIMIT 3
        """)
        research_projects = cursor.fetchall()

        return jsonify({
            "code": 200,
            "msg": "success",
            "data": {
                "research_projects": research_projects,
                "carousel_data": carousel_data
            }
        })
    except Exception as e:
        print(f"获取首页数据失败：{str(e)}")
        return jsonify({"code": 500, "msg": "获取首页数据失败", "data": {}})
    finally:
        cursor.close()
        db.close()

# 武术资讯接口
@app.route('/api/consult', methods=['GET'])
def get_consult_data():
    db = get_db_connection()
    if not db:
        return jsonify({"code": 500, "msg": "数据库连接失败", "data": []})

    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT id, title, SUBSTRING(content, 1, 100) as `desc`,
                   image_url as image, DATE_FORMAT(publish_time, '%Y-%m-%d') as date
            FROM ws_news
            WHERE status = 1
            ORDER BY publish_time DESC
            LIMIT 10
        """)
        news_list = cursor.fetchall()

        return jsonify({
            "code": 200,
            "msg": "success",
            "data": news_list
        })
    except Exception as e:
        print(f"获取资讯数据失败：{str(e)}")
        return jsonify({"code": 500, "msg": "获取资讯数据失败", "data": []})
    finally:
        cursor.close()
        db.close()

# 研学项目列表接口
@app.route('/api/research/list', methods=['GET'])
def get_research_list():
    db = get_db_connection()
    if not db:
        return jsonify({"code": 500, "msg": "数据库连接失败", "data": []})

    cursor = db.cursor()
    try:
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 10))
        offset = (page - 1) * size

        cursor.execute("SELECT COUNT(*) as total FROM ws_research WHERE status = 1")
        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT id, title, `desc`, image_url as image, price, address, days
            FROM ws_research
            WHERE status = 1
            ORDER BY sort ASC
            LIMIT %s OFFSET %s
        """, (size, offset))
        list_data = cursor.fetchall()

        return jsonify({
            "code": 200,
            "msg": "success",
            "data": {
                "list": list_data,
                "total": total,
                "page": page,
                "size": size
            }
        })
    except Exception as e:
        print(f"获取研学项目失败：{str(e)}")
        return jsonify({"code": 500, "msg": "获取研学项目失败", "data": []})
    finally:
        cursor.close()
        db.close()

# 研学报名接口
@app.route('/api/enroll', methods=['POST'])
def enroll_research():
    data = request.json
    user_id = data.get('userId')
    research_id = data.get('researchId')
    real_name = data.get('realName')
    phone = data.get('phone')
    id_card = data.get('idCard')
    enroll_time = data.get('enrollTime')

    if not all([user_id, research_id, real_name, phone]):
        return jsonify({"code": 400, "msg": "必填参数不能为空"})
    if not re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify({"code": 400, "msg": "手机号格式错误"})

    db = get_db_connection()
    if not db:
        return jsonify({"code": 500, "msg": "数据库连接失败"})

    cursor = db.cursor()
    try:
        sql = """
            INSERT INTO ws_enroll
            (user_id, research_id, real_name, phone, id_card, enroll_time, create_time, update_time)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        cursor.execute(sql, (user_id, research_id, real_name, phone, id_card, enroll_time))
        db.commit()

        return jsonify({"code": 200, "msg": "报名成功，等待审核"})
    except Exception as e:
        db.rollback()
        print(f"报名失败：{str(e)}")
        return jsonify({"code": 500, "msg": "报名失败"})
    finally:
        cursor.close()
        db.close()

# ---------------------- 管理后台-数据统计接口 ----------------------
@app.route('/admin/api/stats', methods=['GET'])
@admin_login_required
def get_admin_stats():
    db = get_db_connection()
    if not db:
        return jsonify({"code": 500, "msg": "数据库连接失败", "data": {}})
    
    cursor = db.cursor()
    try:
        cursor.execute("SELECT COUNT(*) as total FROM ws_user")
        user_total = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM ws_research WHERE status = 1")
        project_total = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM ws_news WHERE status = 1")
        news_total = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM ws_enroll")
        application_total = cursor.fetchone()['total']

        return jsonify({
            "code": 200,
            "msg": "success",
            "data": {
                "user_total": user_total,
                "project_total": project_total,
                "news_total": news_total,
                "application_total": application_total
            }
        })
    except Exception as e:
        print(f"获取统计数据失败: {str(e)}")
        return jsonify({"code": 500, "msg": "获取数据异常", "data": {}})
    finally:
        cursor.close()
        db.close()

# ---------------------- 研学项目管理接口 ----------------------
# 项目图片访问路由
@app.route('/uploads/project/<filename>')
def serve_project_img(filename):
    return send_from_directory('uploads/project', filename)

# 1. 获取研学项目列表
@app.route('/admin/api/research/list', methods=['GET'])
@admin_login_required
def admin_get_research_list():
    db = get_db_connection()
    if not db:
        return jsonify({"code": 500, "msg": "数据库连接失败", "data": {"list": [], "total": 0}})

    cursor = db.cursor()
    try:
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 10))
        keyword = request.args.get('keyword', '').strip()
        status = request.args.get('status', '')

        offset = (page - 1) * size
        params = []
        where_sql = " WHERE 1=1 "

        if keyword:
            where_sql += " AND title LIKE %s "
            params.append(f"%{keyword}%")
        if status != '':
            where_sql += " AND status = %s "
            params.append(status)

        count_sql = "SELECT COUNT(*) as total FROM ws_research " + where_sql
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']

        sql = """
            SELECT id, title, `desc`, image_url, price, address, days, status,
                   DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') as create_time
            FROM ws_research
        """ + where_sql + " ORDER BY create_time DESC LIMIT %s OFFSET %s"

        params.extend([size, offset])
        cursor.execute(sql, params)
        list_data = cursor.fetchall()

        return jsonify({
            "code": 200,
            "msg": "success",
            "data": {
                "list": list_data,
                "total": total,
                "page": page,
                "size": size
            }
        })
    except Exception as e:
        print("获取项目列表错误：", str(e))
        return jsonify({"code": 500, "msg": "获取项目失败", "data": {"list": [], "total": 0}})
    finally:
        cursor.close()
        db.close()

# 2. 新增研学项目
@app.route('/admin/api/research/add', methods=['POST'])
@admin_login_required
def admin_add_research():
    try:
        title = request.form.get('title')
        desc = request.form.get('desc', '')
        price = request.form.get('price', 0)
        days = request.form.get('days', 1)
        address = request.form.get('address', '')
        status = request.form.get('status', 1)
        file = request.files.get('image_url')

        if not title:
            return jsonify({"code": 400, "msg": "项目名称不能为空"})

        image_url = ''
        if file and file.filename != '':
            upload_folder = 'uploads/project'
            os.makedirs(upload_folder, exist_ok=True)
            ext = os.path.splitext(file.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(upload_folder, filename)
            file.save(save_path)
            image_url = f"uploads/project/{filename}"

        db = get_db_connection()
        cursor = db.cursor()
        sql = """
            INSERT INTO ws_research
            (title, `desc`, image_url, price, days, address, status, sort, create_time, update_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 99, NOW(), NOW())
        """
        cursor.execute(sql, (title, desc, image_url, price, days, address, status))
        db.commit()

        return jsonify({"code": 200, "msg": "新增成功"})
    except Exception as e:
        db.rollback()
        print("新增错误：", str(e))
        return jsonify({"code": 500, "msg": "新增失败"})
    finally:
        cursor.close()
        db.close()

# 3. 编辑研学项目
@app.route('/admin/api/research/edit', methods=['POST'])
@admin_login_required
def admin_edit_research():
    try:
        id = request.form.get('id')
        title = request.form.get('title')
        desc = request.form.get('desc', '')
        price = request.form.get('price', 0)
        days = request.form.get('days', 1)
        address = request.form.get('address', '')
        status = request.form.get('status', 1)
        file = request.files.get('image_url')

        if not id or not title:
            return jsonify({"code": 400, "msg": "参数错误"})

        db = get_db_connection()
        cursor = db.cursor()

        image_sql = ""
        params = []
        if file and file.filename != '':
            upload_folder = 'uploads/project'
            os.makedirs(upload_folder, exist_ok=True)
            ext = os.path.splitext(file.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(upload_folder, filename)
            file.save(save_path)
            image_url = f"uploads/project/{filename}"
            image_sql = " image_url = %s, "
            params.append(image_url)

        params.extend([title, desc, price, days, address, status, id])
        sql = f"""
            UPDATE ws_research SET
                {image_sql} title=%s, `desc`=%s, price=%s, days=%s, address=%s,
                status=%s, update_time=NOW()
            WHERE id=%s
        """
        cursor.execute(sql, params)
        db.commit()

        return jsonify({"code": 200, "msg": "修改成功"})
    except Exception as e:
        db.rollback()
        print("编辑错误：", str(e))
        return jsonify({"code": 500, "msg": "修改失败"})
    finally:
        cursor.close()
        db.close()

# 4. 删除研学项目
@app.route('/admin/api/research/delete', methods=['POST'])
@admin_login_required
def admin_delete_research():
    id = request.json.get('id')
    if not id:
        return jsonify({"code": 400, "msg": "参数错误"})

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM ws_research WHERE id=%s", (id,))
        db.commit()
        return jsonify({"code": 200, "msg": "删除成功"})
    except:
        db.rollback()
        return jsonify({"code": 500, "msg": "删除失败"})
    finally:
        cursor.close()
        db.close()

# 5. 批量删除
@app.route('/admin/api/research/batch-delete', methods=['POST'])
@admin_login_required
def admin_batch_delete_research():
    ids = request.json.get('ids', [])
    if not ids:
        return jsonify({"code": 400, "msg": "请选择项目"})

    db = get_db_connection()
    cursor = db.cursor()
    try:
        placeholder = ', '.join(['%s'] * len(ids))
        cursor.execute(f"DELETE FROM ws_research WHERE id IN ({placeholder})", ids)
        db.commit()
        return jsonify({"code": 200, "msg": "批量删除成功"})
    except:
        db.rollback()
        return jsonify({"code": 500, "msg": "批量删除失败"})
    finally:
        cursor.close()
        db.close()

# 6. 上下线切换
@app.route('/admin/api/research/change-status', methods=['POST'])
@admin_login_required
def admin_change_research_status():
    data = request.json
    id = data.get('id')
    status = data.get('status')

    if not id or status not in [0, 1]:
        return jsonify({"code": 400, "msg": "参数错误"})

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("UPDATE ws_research SET status=%s WHERE id=%s", (status, id))
        db.commit()
        return jsonify({"code": 200, "msg": "状态修改成功"})
    except:
        db.rollback()
        return jsonify({"code": 500, "msg": "状态修改失败"})
    finally:
        cursor.close()
        db.close()


@app.route('/api/projects', methods=['GET'])
@admin_login_required
def api_projects_list():
    db = get_db_connection()
    if not db:
        return jsonify({"code":500,"data":{"list":[],"total":0}})
    cursor = db.cursor()
    page = int(request.args.get('page',1))
    size = int(request.args.get('size',10))
    keyword = request.args.get('keyword','')
    status = request.args.get('status','')
    offset = (page-1)*size
    w = "1=1"
    p = []
    if keyword:
        w+=" AND title like %s"
        p.append(f"%{keyword}%")
    if status!='':
        w+=" AND status=%s"
        p.append(status)
    cursor.execute(f"SELECT count(*) total FROM ws_research WHERE {w}",p)
    total = cursor.fetchone()['total']
    cursor.execute(f"""
        SELECT id,title as name,title,`desc` as description,
        days as duration,price,image_url as cover_img,status,
        DATE_FORMAT(create_time,'%Y-%m-%d %H:%i:%s') as create_time
        FROM ws_research WHERE {w} ORDER BY create_time desc LIMIT %s OFFSET %s
    """,p+[size,offset])
    li = cursor.fetchall()
    return jsonify({"code":200,"data":{"list":li,"total":total}})

@app.route('/api/projects/<int:id>',methods=['GET'])
@admin_login_required
def api_project_detail(id):
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("""
        SELECT id,title as name,`desc` as description,days as duration,price,
        image_url as cover_img,status FROM ws_research WHERE id=%s
    """,[id])
    return jsonify({"code":200,"data":cursor.fetchone()})

@app.route('/api/projects',methods=['POST'])
@admin_login_required
def api_project_add():
    request.form = request.form.copy()
    request.form['title'] = request.form.get('name','')
    request.form['desc'] = request.form.get('description','')
    request.form['days'] = request.form.get('duration',1)
    if 'cover_img' in request.files:
        request.files['image_url'] = request.files['cover_img']
    return admin_add_research()

@app.route('/api/projects/<int:id>',methods=['PUT'])
@admin_login_required
def api_project_edit(id):
    request.form = request.form.copy()
    request.form['id']=str(id)
    request.form['title']=request.form.get('name','')
    request.form['desc']=request.form.get('description','')
    request.form['days']=request.form.get('duration',1)
    if 'cover_img' in request.files:
        request.files['image_url']=request.files['cover_img']
    return admin_edit_research()

@app.route('/api/projects/<int:id>',methods=['DELETE'])
@admin_login_required
def api_project_del(id):
    request.json={'id':id}
    return admin_delete_research()

@app.route('/api/projects/batch',methods=['DELETE'])
@admin_login_required
def api_project_batch_del():
    return admin_batch_delete_research()

@app.route('/api/projects/<int:id>/status',methods=['PUT'])
@admin_login_required
def api_project_status(id):
    request.json={'id':id,'status':request.json.get('status')}
    return admin_change_research_status()

# ---------------------- 页面路由 ----------------------
@app.route('/admin/login.html')
def admin_login_page():
    return send_file('admin.html')

@app.route('/admin/index.html')
@admin_login_required
def admin_index():
    return send_file('admin_index.html')

@app.route('/admin/user.html')
@admin_login_required
def admin_user_manage():
    return send_file('admin_user.html')

@app.route('/admin/research.html')
@admin_login_required
def admin_research_manage():
    return send_file('admin_research.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin/login.html')

@app.route('/login.html')
def login():
    return send_file('login.html')

@app.route('/forget.html')
def forget_password():
    return send_file('forget.html')

@app.route('/register.html')
def register():
    return send_file('register.html')

@app.route('/')
@app.route('/index.html')
def index():
    return send_file('index.html')

@app.route('/consult.html')
def consult():
    return send_file('consult.html')

@app.route('/research.html')
def research():
    return send_file('research.html')

@app.route('/exchange.html')
def exchange():
    return send_file('exchange.html')

# ---------------------- 个人中心页面----------------------
@app.route('/profile.html')
@user_login_required
def profile_page():
    return send_file('profile.html')

# ---------------------- 用户退出登录 ----------------------
@app.route('/logout')
def user_logout():
    session.clear()
    return redirect('/login.html')

# ---------------------- 管理员接口 ----------------------
# 管理员登录接口
@app.route('/admin/api/login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"code": 400, "msg": "账号或密码不能为空"})

    db = get_db_connection()
    if not db:
        return jsonify({"code": 500, "msg": "数据库连接失败"})

    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT id, username, password, nickname, role, status
            FROM ws_admin
            WHERE username = %s
        """, (username,))
        admin = cursor.fetchone()

        if not admin:
            return jsonify({"code": 400, "msg": "管理员账号不存在"})
        if admin['status'] == 0:
            return jsonify({"code": 400, "msg": "账号已禁用，请联系超级管理员"})

        if not check_password_hash(admin['password'], password):
            return jsonify({"code": 400, "msg": "密码错误"})

        session['admin_id'] = admin['id']
        session['admin_username'] = admin['username']
        session['admin_role'] = admin['role']

        cursor.execute("""
            UPDATE ws_admin
            SET last_login_time = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (admin['id'],))
        db.commit()

        return jsonify({
            "code": 200,
            "msg": "登录成功",
            "data": {
                "id": admin['id'],
                "username": admin['username'],
                "nickname": admin['nickname'],
                "role": admin['role']
            }
        })
    except Exception as e:
        print(f"管理员登录异常：{str(e)}")
        return jsonify({"code": 500, "msg": "登录失败，请重试"})
    finally:
        cursor.close()
        db.close()

# ---------------------- 管理员-用户管理接口 ----------------------
# 1. 获取用户列表
@app.route('/admin/api/user/list', methods=['GET'])
@admin_login_required
def admin_get_user_list():
    db = get_db_connection()
    if not db:
        return jsonify({"code": 500, "msg": "数据库连接失败", "data": {}})

    cursor = db.cursor()
    try:
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 10))
        offset = (page - 1) * size
        keyword = request.args.get('keyword', '').strip()

        base_sql = """ FROM ws_user WHERE 1=1 """
        params = []

        if keyword:
            base_sql += " AND (phone LIKE %s OR username LIKE %s)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        count_sql = "SELECT COUNT(*) as total " + base_sql
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']

        list_sql = """
            SELECT id, username, phone, email, avatar, status,
                   DATE_FORMAT(create_time, '%%Y-%%m-%%d %%H:%%i:%%s') as create_time,
                   DATE_FORMAT(update_time, '%%Y-%%m-%%d %%H:%%i:%%s') as update_time
        """ + base_sql + " ORDER BY create_time DESC LIMIT %s OFFSET %s"

        params.extend([size, offset])
        cursor.execute(list_sql, params)
        user_list = cursor.fetchall()

        return jsonify({
            "code": 200,
            "msg": "success",
            "data": {
                "list": user_list,
                "total": total,
                "page": page,
                "size": size
            }
        })
    except Exception as e:
        print(f"【错误详情】: {str(e)}")
        return jsonify({"code": 500, "msg": f"获取用户列表失败: {str(e)}", "data": {}})
    finally:
        cursor.close()
        db.close()

# 2. 修改用户状态
@app.route('/admin/api/user/change-status', methods=['POST'])
@admin_login_required
def admin_change_user_status():
    data = request.json
    user_id = data.get('userId')
    status = data.get('status')

    if not user_id or status not in [0, 1]:
        return jsonify({"code": 400, "msg": "参数错误"})

    db = get_db_connection()
    if not db:
        return jsonify({"code": 500, "msg": "数据库连接失败"})

    cursor = db.cursor()
    try:
        cursor.execute("""
            UPDATE ws_user
            SET status = %s, update_time = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (status, user_id))
        db.commit()

        return jsonify({"code": 200,"msg": "用户状态修改成功"})
    except Exception as e:
        db.rollback()
        print(f"修改用户状态失败：{str(e)}")
        return jsonify({"code": 500, "msg": "修改用户状态失败"})
    finally:
        cursor.close()
        db.close()

# 3. 删除用户接口
@app.route('/admin/api/user/delete', methods=['POST'])
@admin_login_required
def admin_delete_user():
    data = request.json
    user_id = data.get('userId')
    if not user_id:
        return jsonify({"code": 400, "msg": "参数错误"})

    db = get_db_connection()
    if not db:
        return jsonify({"code": 500, "msg": "数据库连接失败"})

    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM ws_user WHERE id = %s", (user_id,))
        db.commit()
        return jsonify({"code": 200, "msg": "删除成功"})
    except Exception as e:
        db.rollback()
        return jsonify({"code": 500, "msg": "删除失败"})
    finally:
        cursor.close()
        db.close()

# 4. 批量删除用户
@app.route('/admin/api/user/batch-delete', methods=['POST'])
@admin_login_required
def admin_batch_delete_user():
    ids = request.json.get('ids', [])
    if not ids:
        return jsonify({"code": 400, "msg": "请选择用户"})

    db = get_db_connection()
    if not db:
        return jsonify({"code": 500, "msg": "数据库连接失败"})

    cursor = db.cursor()
    try:
        placeholders = ', '.join(['%s'] * len(ids))
        cursor.execute(f"DELETE FROM ws_user WHERE id IN ({placeholders})", ids)
        db.commit()
        return jsonify({"code": 200,"msg": "批量删除成功"})
    except Exception as e:
        db.rollback()
        print(f"批量删除失败：{str(e)}")
        return jsonify({"code": 500, "msg": "批量删除失败"})
    finally:
        cursor.close()
        db.close()

# ---------------------- 用户相关接口 ----------------------
# 用户注册接口
@app.route('/api/register', methods=['POST'])
def api_register():
    username = request.form.get('username')
    phone = request.form.get('phone')
    password = request.form.get('password')
    code = request.form.get('code')
    avatar = request.files.get('avatar')

    if not phone or not username or not password:
        return jsonify({"code":400,"msg":"信息不能为空"})

    if code != "123456":
        return jsonify({"code":400,"msg":"验证码错误"})

    db = get_db_connection()
    if not db:
        return jsonify({"code":500,"msg":"数据库连接失败"})

    cursor = db.cursor()

    try:
        cursor.execute("SELECT id FROM ws_user WHERE phone=%s", (phone,))
        if cursor.fetchone():
            return jsonify({"code":400,"msg":"手机号已注册"})

        pwd_hash = generate_password_hash(password, method='pbkdf2:sha256')

        avatar_filename = None
        if avatar:
            upload_folder = 'uploads/avatar'
            os.makedirs(upload_folder, exist_ok=True)

            ext = os.path.splitext(avatar.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(upload_folder, filename)
            avatar.save(save_path)

            avatar_filename = f'uploads/avatar/{filename}'

        sql = """
        INSERT INTO ws_user
        (phone, username, password, avatar, email, status, create_time, update_time)
        VALUES (%s, %s, %s, %s, '', 1, NOW(), NOW())
        """
        cursor.execute(sql, (phone, username, pwd_hash, avatar_filename))
        db.commit()

        return jsonify({"code":200,"msg":"注册成功"})

    except Exception as e:
        db.rollback()
        print("❌ 注册失败原因：", str(e))
        return jsonify({"code":500,"msg":"注册失败：" + str(e)})
    finally:
        cursor.close()
        db.close()

# 用户登录接口
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    account = data.get('account')
    password = data.get('password')

    if not account or not password:
        return jsonify({"code": 400, "msg": "参数不能为空"})

    db = get_db_connection()
    if not db:
        return jsonify({"code": 500, "msg": "数据库连接失败"})

    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT id, username, password, avatar, status, phone, email
            FROM ws_user
            WHERE BINARY phone = %s
        """, (account,))
        user = cursor.fetchone()

        if not user:
            cursor.execute("""
                SELECT id, username, password, avatar, status, phone, email
                FROM ws_user
                WHERE BINARY username = %s
            """, (account,))
            user = cursor.fetchone()

        if not user:
            return jsonify({"code": 400, "msg": "账号未注册"})

        if str(user['status']).strip() == '0':
            return jsonify({"code": 400, "msg": "账号已被禁用，请联系管理员"})

        if not check_password_hash(user['password'], password):
            return jsonify({"code": 400, "msg": "密码错误"})

        session['user_id'] = user['id']
        session['username'] = user['username']
        session['phone'] = user['phone']
        session['avatar'] = user['avatar']
        session['email'] = user.get('email', '')

        return jsonify({
            "code": 200,
            "msg": "login successful",
            "data": {
                "id": user['id'],
                "username": user['username'],
                "avatar": user['avatar'],
                "phone": user['phone']
            }
        })
    except Exception as e:
        print(f"登录异常：{str(e)}")
        return jsonify({"code": 500, "msg": "登录失败"})
    finally:
        cursor.close()
        db.close()

# ---------------------- 获取当前登录用户信息 ----------------------
@app.route('/api/user/info', methods=['GET'])
@user_login_required
def user_info():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"code":401,"msg":"未登录"})
    
    db = get_db_connection()
    if not db:
        return jsonify({"code":500,"msg":"数据库连接失败"})
    
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT id, username, phone, email, avatar, create_time
            FROM ws_user WHERE id = %s
        """, (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"code":404,"msg":"用户不存在"})

        if user.get('avatar'):
            user['avatar'] = "/" + user['avatar']

        return jsonify({"code":200,"data":user})
    except Exception as e:
        print(f"获取用户信息异常: {e}")
        return jsonify({"code":500,"msg":f"获取用户信息失败: {str(e)}"})
    finally:
        cursor.close()
        db.close()

# 忘记密码：获取验证码
@app.route('/api/forget/send-code', methods=['POST'])
def send_forget_code():
    phone = request.json.get('phone')
    if not phone or not re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify({"code": 400, "msg": "手机号格式错误"})

    db = get_db_connection()
    if not db:
        return jsonify({"code": 500, "msg": "数据库连接失败"})

    cursor = db.cursor()
    try:
        cursor.execute("SELECT id FROM ws_user WHERE phone = %s", (phone,))
        if not cursor.fetchone():
            return jsonify({"code": 400, "msg": "手机号未注册"})

        return jsonify({"code": 200, "msg": "验证码已发送，验证码：123456"})
    except Exception as e:
        print(f"发送验证码失败：{str(e)}")
        return jsonify({"code": 500, "msg": "发送验证码失败：{str(e)}"})
    finally:
        cursor.close()
        db.close()

# 忘记密码：重置密码
@app.route('/api/forget/reset', methods=['POST'])
def reset_password():
    data = request.json
    phone = data.get('phone')
    code = data.get('code')
    new_pwd = data.get('newPassword')

    if not phone or not re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify({"code": 400, "msg": "手机号格式错误"})
    if code != "123456":
        return jsonify({"code": 400, "msg": "验证码错误"})
    if not re.match(r'^(?=.*[a-zA-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=.\[\]{}|~`])[a-zA-Z\d!@#$%^&*()_+\-=.\[\]{}|~`]{8,20}$', new_pwd):
        return jsonify({"code": 400, "msg": "密码需为8-20位，包含字母、数字和符号"})

    db = get_db_connection()
    if not db:
        return jsonify({"code": 500, "msg": "数据库连接失败"})

    cursor = db.cursor()
    try:
        cursor.execute("SELECT id FROM ws_user WHERE phone = %s", (phone,))
        if not cursor.fetchone():
            return jsonify({"code": 400, "msg": "手机号未注册"})

        new_pwd_hash = generate_password_hash(new_pwd, method='pbkdf2:sha256')

        sql = "UPDATE ws_user SET password = %s, update_time = CURRENT_TIMESTAMP WHERE phone = %s"
        cursor.execute(sql, (new_pwd_hash, phone))
        db.commit()

        return jsonify({"code": 200, "msg": "密码重置成功"})
    except Exception as e:
        db.rollback()
        print(f"重置密码失败：{str(e)}")
        return jsonify({"code": 500, "msg": "重置密码失败：{str(e)}"})
    finally:
        cursor.close()
        db.close()

# ---------------------- 启动服务 ----------------------
if __name__=='__main__':
    test_db = get_db_connection()
    if test_db:
        print("数据库连接成功！")
        test_db.close()

    app.run(debug=True, host='0.0.0.0', port=5000)