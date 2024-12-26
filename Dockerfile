# 建立 python 3.9环境
FROM python:3.10

# 安装netcat
RUN apt-get update && apt install -y netcat

# image author
MAINTAINER kdemo

# 设置 python 环境变量
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 可选：设置镜像源为国内
COPY pip.conf /root/.pip/pip.conf

# 容器内创建 myproject 文件夹
ENV APP_HOME=/home/kdemo
RUN mkdir -p $APP_HOME
WORKDIR $APP_HOME

# 将当前目录加入到工作目录中（. 表示当前目录）
ADD . $APP_HOME

# 解压打包后的前端静态文件
# RUN tar -xvf frontend/dist.tar --strip-components 1 -C frontend
# RUN unzip -o frontend/dist.zip -d frontend/

# 移除\r in windows
RUN sed -i 's/\r//' ./start.sh

# 给start.sh可执行权限
RUN chmod +x ./start.sh

# 数据迁移，并使用uwsgi启动服务
ENTRYPOINT /bin/bash ./start.sh