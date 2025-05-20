// 导航栏交互功能
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', function() {
            navLinks.classList.toggle('active');
        });

        // 点击导航链接后关闭菜单
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('active');
            });
        });

        // 点击页面其他区域关闭菜单
        document.addEventListener('click', function(event) {
            const isClickInside = navToggle.contains(event.target) || navLinks.contains(event.target);
            if (!isClickInside && navLinks.classList.contains('active')) {
                navLinks.classList.remove('active');
            }
        });
    }

    // 滚动时添加阴影效果
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 10) {
                navbar.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
            } else {
                navbar.style.boxShadow = 'none';
            }
        });
    }
});