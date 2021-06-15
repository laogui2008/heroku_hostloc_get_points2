# heroku_hostloc_get_points
利用heroku，登录hostloc，访问用户空间，获取积分  
签到成功，将积分、威望、金钱等数据发送到TG  
原项目代码：[https://git.inkuang.com/inkuang/hostloc-auto-get-points](https://git.inkuang.com/inkuang/hostloc-auto-get-points)  


#### 更新说明  
2021-06-15  
定时任务增加misfire_grace_time参数解决Run time of job...next run at...was missed by问题    
参考：[Missed job executions and coalescing](https://apscheduler.readthedocs.io/en/3.0/userguide.html#missed-job-executions-and-coalescing)  



#### 注意
1. 适合有编程基础和对heroku cli操作比较了解的人使用  
2. heroku免费时长为550小时(**运行该脚本可能会用完该免费时长**)，添加信用卡认证后可增加450小时，总共1000小时  
3. **代码中的send_points_to_tg_flag字段，用于控制是否发送消息到TG，True-发送，False-不发送**  
3. 需要设置的环境变量：**HOSTLOC_USERNAME(必要)、HOSTLOC_PASSWORD(必要)、TG_CHAT_ID(可选，send_points_to_tg_flag=True时必要)、TG_BOT_TOKEN(可选，send_points_to_tg_flag=True时必要)**  


#### 使用说明
1. 发送消息到TG准备事项 (如果不需要发送消息到TG，该步骤可忽略)  
    a. 私聊[BotFather](https://t.me/botfather)，根据提示，创建一个机器人  
    b. 记录下机器人的token(**即后续步骤设置的环境变量TG_BOT_TOKEN**)，如：1234567890:AAG2yuabcdLcmefg-0ovWhkJlOpqEf0Jabc  
    c. 与创建的机器人聊天，随便发一条消息，然后转发至[GetIDs Bot](https://t.me/getidsbot)，得到用户id(**即后续步骤设置的环境变量TG_CHAT_ID**)  

2. 安装git

3. heroku操作说明 (本人使用环境是Windows 10)  
    a. 注册[heroku账号](https://www.heroku.com/)  
    b. 安装[Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)  
    c. 打开cmd，在浏览器heroku账号已登录的情况下，可直接运行命令：heroku login，在浏览器上进行授权登录；在浏览器heroku账号未登录的情况下，直接运行命令：heroku login -i，根据提示，输入账号和密码登录  
    ![heroku login](/static/1.png)  
    d. 修改代码中变量send_points_to_tg_flag的值，设置是否发送消息到TG  
    ![send_points_to_tg_flag](/static/3.png)  
    e. 修改函数main()上注解的值，设置定时任务运行时间(以服务器所在时区为准)，以下例子是每天9：48分运行  
    ![main()](/static/2.png)  
    f. 创建heroku应用  

        cd heroku_hostloc_get_points2
        heroku create hostloc-get-points2

    g. 提交代码，初始化项目  

        git add .
        git commit -m "init"
        git push heroku main

    h. 设置环境变量  

        heroku config:set HOSTLOC_USERNAME="user1" HOSTLOC_PASSWORD="pass1" --app=hostloc-get-points2    # 设置hostloc的账号密码，如果有多个，用英文逗号,进行分隔
        heroku config:set TG_CHAT_ID="xxxxx" TG_BOT_TOKEN="xxxxxxxxxxxxxxx" --app=hostloc-get-points2    # 设置TG的chat_id和机器人的token，如果不需要发送TG消息，可不用设置

    i. 为heroku应用分配资源，运行项目  

        heroku ps:scale clock=1 --app=hostloc-get-points2 # 分配资源，项目启动    为什么是clock？请看Procfile文件
        heroku ps:scale clock=0 --app=hostloc-get-points2 # 取消资源分配

    j. 查看日志  
    ![log](/static/4.png)  
    ![log](/static/5.png)  
    k. TG上的信息  
    ![log](/static/6.png)  

4. 在上述步骤创建应用运行后，如果本地有修改，如修改定时任务运行时间，需要将修改的代码push到heroku  
    参考：[Heroku Push local changes](https://devcenter.heroku.com/articles/getting-started-with-python#push-local-changes)  
    
        git add .  
        git commit -m "update"  
        git push heroku main  

5. **设置定时任务时间前，先登录heroku服务器，查看当前服务器时间**  
    
        # 用heroku cli登录后，执行下面命令，查看服务时间  
        # hostloc-get-points2是应用名，替换成自己的，可用heroku apps查看所有应用  
        heroku run bash --app=hostloc-get-points2  
        date -R  
        exit    #查看完后记得退出  

    ![heroku run bash --app=hostloc-get-points2](/static/7.png)  

