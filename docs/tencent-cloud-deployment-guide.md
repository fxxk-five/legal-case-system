# 腾讯云上线操作手册

本文档专门面向你当前这个项目，目标是把“本地可演示版”部署到腾讯云，形成一套可以通过域名访问、支持 HTTPS、支持微信小程序正式联调的线上环境。

## 一、上线目标

你要部署完成后，最终应达到以下结果：

- 电脑浏览器可以通过域名访问 Web 管理端
- 后端接口可以通过 HTTPS 域名访问
- 微信小程序可以把这个域名配置为合法域名
- 律师可以登录 Web，创建案件、查看案件、查看文件
- 当事人可以通过小程序进入案件、上传文件、预览文件

## 二、推荐架构

当前项目最适合使用这套架构：

- 腾讯云 `CVM`：部署服务器
- Docker Compose：运行整套服务
- Nginx：统一入口、反向代理、HTTPS 证书接入
- PostgreSQL：数据库
- Redis：缓存和后续任务支持
- 域名解析：DNSPod / 腾讯云解析
- SSL 证书：腾讯云免费证书

推荐访问结构：

- `https://你的域名`
  - Web 前端
- `https://你的域名/api/...`
  - 后端接口服务

## 三、你需要提前准备的内容

### 1. 腾讯云资源

你需要自己购买或准备：

- 一台腾讯云 CVM
- 一个可用域名
- 一张 SSL 证书
- 一个微信小程序正式 `AppID`

### 2. 推荐服务器配置

建议你购买：

- `2核4G` 或 `4核8G`
- Ubuntu 22.04
- 系统盘至少 `50GB`
- 开启公网 IP

### 3. 你本地要准备好的内容

你需要自己确认：

- 项目代码已经推到 Git 仓库，或者你能通过压缩包上传到服务器
- [backend/.env](/D:/code/law/legal-case-system/backend/.env) 里的数据库配置你能看懂并能修改
- 你已经知道自己的微信小程序 `AppID` 和 `AppSecret`

## 四、腾讯云购买与配置顺序

### 第 1 步：购买 CVM

你要做的事：

1. 登录腾讯云控制台
2. 打开云服务器 CVM
3. 购买一台 Linux 服务器
4. 记录服务器公网 IP

建议你在安全组里放行这些端口：

- `22`
- `80`
- `443`

说明：

- `22`：SSH 登录服务器
- `80`：HTTP
- `443`：HTTPS

### 第 2 步：准备域名

你要做的事：

1. 打开腾讯云域名控制台或 DNSPod
2. 给你的域名添加一条 `A 记录`
3. 把域名解析到 CVM 公网 IP

例如：

- `www.你的域名.com` -> 服务器公网 IP
- 或者直接 `你的域名.com` -> 服务器公网 IP

### 第 3 步：申请 SSL 证书

你要做的事：

1. 打开腾讯云 SSL 证书管理
2. 申请免费证书
3. 等域名校验通过
4. 下载 Nginx 证书文件

最终你会拿到：

- 证书文件
- 私钥文件

## 五、服务器初始化

### 第 1 步：登录服务器

你要做的事：

使用 SSH 登录服务器，例如：

```bash
ssh root@你的服务器公网IP
```

### 第 2 步：安装容器环境

你要做的事：

在服务器上安装：

- Docker
- Docker Compose

如果你不熟，我后续可以再专门给你写一份“Ubuntu 安装 Docker 教程”。

### 第 3 步：上传项目代码

你可以任选一种方式：

#### 方式 A：Git 拉取

```bash
git clone 你的仓库地址
cd legal-case-system
```

#### 方式 B：本地打包上传

你要做的事：

- 在本地压缩 `legal-case-system`
- 上传到服务器
- 解压后进入项目目录

## 六、服务器上的环境变量配置

这是上线最关键的一步。

你要做的事：

1. 进入项目目录
2. 编辑 `backend/.env`

生产环境建议至少改成这样：

```env
PROJECT_NAME=法律案件管理系统
VERSION=0.1.0
API_V1_STR=/api/v1

POSTGRES_SERVER=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=你自己设置的强密码
POSTGRES_DB=legal_case

SECRET_KEY=你自己生成的长随机密钥
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

WECHAT_MINIAPP_APP_ID=你的小程序AppID
WECHAT_MINIAPP_APP_SECRET=你的小程序AppSecret
WECHAT_MINIAPP_MOCK_LOGIN=false
WECHAT_MINIAPP_CLIENT_ENTRY_PAGE=pages/client/entry
```

### 你必须自己做的事

- 把数据库密码改成你自己的强密码
- 把 `SECRET_KEY` 改成你自己的随机密钥
- 把 `WECHAT_MINIAPP_MOCK_LOGIN` 改成 `false`
- 填入真实 `AppID` 和 `AppSecret`

## 七、启动线上容器环境

### 第 1 步：启动容器

你要做的事：

```bash
cd 你的项目目录
docker compose up --build -d
```

### 第 2 步：检查容器状态

```bash
docker compose ps
```

你应该看到这些服务都处于运行状态：

- `postgres`
- `redis`
- `backend`
- `web-frontend`
- `nginx`

### 第 3 步：初始化数据库

```bash
docker compose exec backend python init_db.py
```

如果你只是做演示环境，也可以补一份演示数据：

```bash
docker compose exec backend sh -lc "cd /app && python -m app.scripts.generate_demo_data"
```

## 八、配置 Nginx HTTPS

当前项目已经有 Nginx 配置文件，但你上线时要把证书接进去。

你要做的事：

1. 把腾讯云 SSL 证书上传到服务器
2. 放到一个目录，例如：

```bash
/etc/nginx/ssl/
```

3. 修改 Nginx 配置，让它监听 `443`

你最终需要实现的效果：

- `80` 自动跳转到 `443`
- `443` 提供 HTTPS
- `/api/` 代理到后端
- `/` 代理到前端

如果你愿意，我下一步可以直接帮你把当前项目的 HTTPS Nginx 配置写出来。

## 九、配置微信小程序合法域名

### 你必须自己做的事

登录微信公众平台，在小程序后台配置这些合法域名：

- `request 合法域名`
- `uploadFile 合法域名`
- `downloadFile 合法域名`

注意：

- 必须是 `HTTPS`
- 不能带路径
- 域名必须和你线上接口域名一致

例如：

```text
https://api.你的域名.com
```

或者你现在这种统一入口：

```text
https://你的域名.com
```

## 十、上线后的验证顺序

建议你按下面顺序验证。

### 1. 服务器层验证

- [ ] `docker compose ps` 全部为运行状态
- [ ] `docker compose logs backend` 无报错
- [ ] `docker compose logs nginx` 无报错

### 2. 域名层验证

- [ ] 能打开 `https://你的域名`
- [ ] 能打开 `https://你的域名/api/v1/health`
- [ ] 能打开 `https://你的域名/docs` 或后端接口文档入口

### 3. Web 端验证

- [ ] 管理员能登录
- [ ] 能查看案件列表
- [ ] 能打开案件详情
- [ ] 能预览和下载文件
- [ ] 能查看通知

### 4. 小程序验证

- [ ] 小程序能请求后端
- [ ] 能完成微信登录
- [ ] 能进入案件
- [ ] 能上传文件
- [ ] 能预览和下载文件

## 十一、上线后你需要重点改掉的默认内容

当前本地演示阶段可以接受，但正式上线前必须改：

- 默认管理员密码
- 默认数据库密码
- 默认 `SECRET_KEY`
- 模拟微信登录
- 演示账号和演示数据

## 十二、常见问题

### 1. 域名能打开首页，但小程序请求失败

优先检查：

- 是否已经配置微信合法域名
- 是否已经启用 HTTPS
- 域名证书是否有效

### 2. 后端容器启动了，但接口报数据库错误

优先检查：

- `backend/.env` 中数据库密码是否和 PostgreSQL 一致
- `POSTGRES_SERVER` 是否为 `postgres`
- 是否已经执行 `docker compose exec backend python init_db.py`

### 3. Web 可以访问，但接口 404

优先检查：

- Nginx 是否正确代理 `/api/`
- 前端构建时是否使用 `/api/v1`
- 后端容器是否正在运行

### 4. 文件上传后下载不了

当前项目上线初期仍使用本地磁盘文件存储。你要检查：

- 后端挂载的 `storage` 目录是否正常
- 文件是否实际写入容器映射目录
- Nginx 与后端代理是否正常

## 十三、你现在最需要自己做的事

按顺序只做这些：

1. 在腾讯云购买一台 CVM
2. 配好安全组 `22/80/443`
3. 配置域名解析到服务器
4. 申请 SSL 证书
5. 把项目上传到服务器
6. 修改服务器上的 `backend/.env`
7. 执行：

```bash
docker compose up --build -d
docker compose exec backend python init_db.py
```

8. 配置微信小程序合法域名
9. 用浏览器和小程序做全流程验证

## 十四、后续我还能继续帮你做什么

我之后可以继续直接帮你补：

- 腾讯云 HTTPS 版 Nginx 配置
- 服务器初始化命令清单
- COS 对象存储接入
- 小程序正式上线前检查清单
- 数据库自动备份方案
