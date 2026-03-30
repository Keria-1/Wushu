document.addEventListener('DOMContentLoaded', function() {
    // 1. 获取首页数据
    if (window.location.pathname === '/' || window.location.pathname === '/index.html') {
        fetch('/api/index')
            .then(response => response.json())
            .then(data => {
                if (data.code === 200) {
                    console.log('首页数据加载成功：', data.data);
                }
            })
            .catch(error => console.error('加载首页数据失败：', error));
    }

    // 2. 获取武术咨询数据
    if (window.location.pathname === '/consult.html') {
        fetch('/api/consult')
            .then(response => response.json())
            .then(data => {
                if (data.code === 200) {
                    console.log('咨询数据加载成功：', data.data);
                }
            })
            .catch(error => console.error('加载咨询数据失败：', error));
    }

    // 3. 导航栏滚动效果
    window.addEventListener('scroll', function() {
        const navbar = document.querySelector('.navbar');
        if (window.scrollY > 50) {
            navbar.classList.add('navbar-scrolled');
        } else {
            navbar.classList.remove('navbar-scrolled');
        }
    });

    const currentPage = window.location.pathname.split('/').pop();
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => link.classList.remove('active'));
    switch (currentPage) {
        case 'index.html':
        case '':
            document.querySelector('a[href="index.html"]')?.classList.add('active');
            break;
        case 'consult.html':
            document.querySelector('a[href="consult.html"]')?.classList.add('active');
            break;
        case 'research.html':
            document.querySelector('a[href="research.html"]')?.classList.add('active');
            break;
        case 'exchange.html':
            document.querySelector('a[href="exchange.html"]')?.classList.add('active');
            break;
    }
});