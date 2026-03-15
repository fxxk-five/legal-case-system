# 小程序联动演示说明

本文档专门用于演示“小程序上传文件，Web 端看到同一份文件”的联动流程。

## 一、当前状态

当前本地环境已经满足以下条件：

- Docker 服务正在运行
- 后端接口可用
- Web 端可访问
- 数据库里已有 3 个演示案件
- 小程序代码已完成登录、进入案件、上传文件、预览下载逻辑

当前唯一限制：

- `mini-program/manifest.json` 中的 `appid` 还是空的
- 没有真实 `AppID` 时，不能完整走微信开发者工具里的正式小程序运行流程

## 二、这次演示要验证什么

本次演示只验证一条核心链路：

1. Web 端生成案件邀请路径
2. 小程序端以当事人身份进入案件
3. 小程序上传文件
4. 回到 Web 案件详情页刷新
5. Web 看到同一份文件

这就说明：

- 小程序和后端是通的
- Web 和后端是通的
- 小程序上传与 Web 查看是同一套数据

## 三、演示前准备

### 你需要自己做的事

1. 打开 Docker 环境
2. 确认 Web 能打开
3. 用 HBuilderX 打开 `mini-program`
4. 确认 `manifest.json` 中后续 `appid` 的填写位置

### 建议先执行

```powershell
cd D:\code\law\legal-case-system
powershell -ExecutionPolicy Bypass -File .\scripts\docker-smoke-test.ps1
```

如果想确认当前演示案件和邀请路径，可以执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\get-demo-invite.ps1
```

## 四、Web 端演示步骤

### 第 1 步：打开 Web

访问：

```text
http://localhost
```

或者：

```text
http://localhost:8080
```

### 第 2 步：管理员登录

账号：

- 手机号：`13800000000`
- 密码：`admin123456`

### 第 3 步：进入案件详情页

你要做的事：

1. 打开案件列表
2. 进入任意一个演示案件
3. 点击“获取当事人邀请路径”
4. 复制这条路径

## 五、小程序端演示步骤

### 第 1 步：打开项目

你要做的事：

1. 用 HBuilderX 打开 [mini-program](/D:/code/law/legal-case-system/mini-program)
2. 查看 [manifest.json](/D:/code/law/legal-case-system/mini-program/manifest.json)
3. 确认 `appid` 位置

### 第 2 步：确认后端地址

查看：

- [common/config.js](/D:/code/law/legal-case-system/mini-program/common/config.js)

默认地址应为：

```text
http://127.0.0.1:8000/api/v1
```

### 第 3 步：进入当事人页面

目标页面是：

```text
pages/client/entry?token=...
```

也就是 Web 端刚刚拿到的那条邀请路径。

### 第 4 步：走模拟微信登录绑定

你要做的事：

1. 输入手机号
2. 输入姓名
3. 点击“微信登录并绑定”

说明：

- 当前后端仍使用模拟微信登录
- 重点不是验证真实微信登录
- 重点是验证“小程序 -> 后端 -> Web”的数据联动

### 第 5 步：进入案件详情并上传文件

你要做的事：

1. 进入案件详情页
2. 点击“上传材料”
3. 选一份测试文件
4. 上传成功后，确认文件出现在小程序列表里

## 六、回到 Web 验证联动

### 你要做的事

1. 回到 Web 的同一个案件详情页
2. 刷新页面
3. 查看案件文件列表

### 你应该看到

- 小程序刚上传的那份文件
- 文件上传时间
- 上传人信息
- 还能继续在 Web 里预览和下载

## 七、如何判断“小程序和 Web 已联通”

满足以下任一条还不够，必须满足整条链路：

- [ ] Web 能登录
- [ ] 小程序能进入案件
- [ ] 小程序能上传文件
- [ ] Web 刷新后能看到同一份文件

只有这样，才算真正联通。

## 八、当前阻塞点

当前最明确的阻塞点是：

- 你还没有真实 `AppID`

这意味着：

- 可以先完成流程准备
- 可以先确认页面、接口、上传逻辑都在
- 但不能把这次演示定义成“真实微信小程序正式联调”

## 九、你现在必须自己做的事

- [ ] 打开 `http://localhost`
- [ ] 用管理员账号登录
- [ ] 进入演示案件详情页
- [ ] 点击“获取当事人邀请路径”
- [ ] 用 HBuilderX 打开 `mini-program`
- [ ] 查看 `manifest.json` 中 `appid` 位置
- [ ] 确认 `common/config.js` 仍然指向本地后端
- [ ] 拿到真实 AppID 后，再接微信开发者工具做正式联动

## 十、如果你只想先证明“Web 和后端是通的”

直接执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\docker-smoke-test.ps1
```

## 十一、如果你想快速拿一条演示邀请路径

直接执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\get-demo-invite.ps1
```
