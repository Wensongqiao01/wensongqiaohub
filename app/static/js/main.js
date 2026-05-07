/* 导航和通用功能 */

document.addEventListener('DOMContentLoaded', function () {
  // 汉堡菜单切换
  const hamburger = document.querySelector('.nav__hamburger');
  const navLinks = document.querySelector('.nav__links');

  if (hamburger && navLinks) {
    hamburger.addEventListener('click', function () {
      navLinks.classList.toggle('nav__links--open');
    });

    // 点击导航项后关闭菜单
    navLinks.querySelectorAll('.nav__link').forEach(function (link) {
      link.addEventListener('click', function () {
        navLinks.classList.remove('nav__links--open');
      });
    });
  }

  // 删除确认对话框
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      var message = el.getAttribute('data-confirm') || '确定要执行此操作吗？';
      var href = el.getAttribute('href') || el.getAttribute('data-href');

      showConfirm(message, function () {
        if (href) {
          if (el.getAttribute('data-method') === 'post') {
            var form = document.createElement('form');
            form.method = 'POST';
            form.action = href;
            document.body.appendChild(form);
            form.submit();
          } else {
            window.location.href = href;
          }
        }
      });
    });
  });
});

/**
 * 显示确认对话框
 * @param {string} message - 确认消息
 * @param {Function} onConfirm - 确认后的回调
 */
function showConfirm(message, onConfirm) {
  var overlay = document.createElement('div');
  overlay.className = 'confirm-overlay';

  var dialog = document.createElement('div');
  dialog.className = 'confirm-dialog';

  dialog.innerHTML =
    '<p class="confirm-dialog__title">确认操作</p>' +
    '<p>' + escapeHtml(message) + '</p>' +
    '<div class="confirm-dialog__actions">' +
    '<button class="btn btn--outline" id="confirm-cancel">取消</button>' +
    '<button class="btn btn--primary" id="confirm-ok">确定</button>' +
    '</div>';

  overlay.appendChild(dialog);
  document.body.appendChild(overlay);

  // 聚焦到取消按钮
  document.getElementById('confirm-cancel').focus();

  function close() {
    document.body.removeChild(overlay);
  }

  document.getElementById('confirm-cancel').addEventListener('click', close);
  document.getElementById('confirm-ok').addEventListener('click', function () {
    close();
    onConfirm();
  });

  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) close();
  });
}

/**
 * HTML 转义
 * @param {string} text
 * @returns {string}
 */
function escapeHtml(text) {
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}
