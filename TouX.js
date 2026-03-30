 document.addEventListener('DOMContentLoaded', function () {
            const userStr = localStorage.getItem('user');
            let user = null;
            try {
                user = JSON.parse(userStr);
            } catch (e) {
                user = null;
            }

            const loginRegBtn = document.getElementById('loginRegBtn');
            const userMenu = document.getElementById('userMenu');
            const navAvatar = document.getElementById('navAvatar');
            const navUsername = document.getElementById('navUsername');

            // 默认头像
            const defaultAvatar = "/static/images/default-avatar.png";

            if (user && user.username) {
                loginRegBtn.style.display = 'none';
                userMenu.classList.remove('d-none');

                if (user.avatar && user.avatar.trim() !== '') {
                    let avatarPath = user.avatar;
                    avatarPath = avatarPath.replace(/\\/g, '/');
                    if (!avatarPath.startsWith('/static')) {
                        avatarPath = '/static' + avatarPath;
                    }
                    navAvatar.src = avatarPath;
                } else {
                    navAvatar.src = defaultAvatar;
                }
                
                navUsername.innerText = user.username;
            } else {
                loginRegBtn.style.display = 'block';
                userMenu.classList.add('d-none');
                navAvatar.src = defaultAvatar;
            }

            // 图片加载失败兜底
            navAvatar.onerror = function () {
                this.src = defaultAvatar;
            };
        });

        // 退出登录
        function logout() {
            if (confirm('确定要退出登录吗？')) {
                localStorage.removeItem('user');
                localStorage.removeItem('userInfo');
                location.reload();
            }
        }