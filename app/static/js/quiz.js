/**
 * 测验游戏状态机
 *
 * 阶段: welcome -> playing -> reviewing -> submitting -> results
 */

(function () {
  'use strict';

  var LETTERS = ['A', 'B', 'C', 'D'];
  var CONTAINER = document.getElementById('quiz-app');

  // 从页面获取题目数据
  var scriptTag = document.getElementById('quiz-data');
  if (!scriptTag) return;

  var allQuestions;
  try {
    allQuestions = JSON.parse(scriptTag.textContent);
  } catch (e) {
    CONTAINER.innerHTML = '<div class="empty-state"><p>数据加载失败，请刷新重试。</p></div>';
    return;
  }

  // ==================== 状态 ====================
  var state = {
    phase: 'welcome',
    questions: allQuestions,
    currentIndex: 0,
    answers: [],   // [{qId, selected}]
    results: null,
    submitting: false,
  };

  // ==================== 工具函数 ====================
  function getBestScore() {
    try {
      return parseInt(localStorage.getItem('quiz_best') || '0', 10);
    } catch (e) {
      return 0;
    }
  }

  function saveBestScore(score) {
    try {
      var prev = getBestScore();
      if (score > prev) {
        localStorage.setItem('quiz_best', String(score));
      }
    } catch (e) {
      // localStorage 不可用时忽略
    }
  }

  function getMessage(percentage) {
    if (percentage === 100) return { text: '太厉害了！你完全了解我！🎉', level: 'perfect' };
    if (percentage >= 80) return { text: '很棒！你对我很了解！', level: 'great' };
    if (percentage >= 60) return { text: '不错，还有进步空间！', level: 'good' };
    return { text: '看来你还需要多了解我一些 😊', level: 'needs-improvement' };
  }

  // ==================== 渲染函数 ====================
  function render() {
    switch (state.phase) {
      case 'welcome':
        renderWelcome();
        break;
      case 'playing':
        renderQuestion();
        break;
      case 'reviewing':
        renderReview();
        break;
      case 'results':
        renderResults();
        break;
      default:
        CONTAINER.innerHTML = '<p>未知状态</p>';
    }
  }

  function renderWelcome() {
    var best = getBestScore();
    var html =
      '<div class="quiz-welcome">' +
      '<h1 class="quiz-welcome__title">📝 对我的了解程度</h1>' +
      '<p class="quiz-welcome__desc">' +
      '这里有 <strong>' + state.questions.length + '</strong> 道关于我的问题。' +
      '试试你能答对多少，也帮我了解大家眼中的我！' +
      '</p>';

    if (best > 0) {
      html += '<p style="margin-bottom: var(--space-6); color: var(--text-secondary);">最高分: <strong style="color: var(--accent);">' + best + '%</strong></p>';
    }

    if (state.questions.length === 0) {
      html += '<div class="empty-state"><p>测验正在准备中，敬请期待...</p></div>';
    } else {
      html += '<button class="btn btn--primary" onclick="window.__quizStart()">开始测验</button>';
    }

    html += '</div>';
    CONTAINER.innerHTML = html;

    // 注册全局函数以便 onclick 调用
    window.__quizStart = function () {
      state.phase = 'playing';
      state.currentIndex = 0;
      state.answers = state.questions.map(function (q) {
        return { qId: q.id, selected: null };
      });
      render();
    };
  }

  function _buildProgressHtml(current, total) {
    var progress = (current / total) * 100;
    return (
      '<div class="quiz-progress">' +
      '<div class="quiz-progress__text">第 ' + current + ' / ' + total + ' 题</div>' +
      '<div class="progress-bar"><div class="progress-bar__fill" style="width: ' + progress + '%;"></div></div>' +
      '</div>'
    );
  }

  function _buildOptionsHtml(q, answer) {
    var html = '<div class="quiz-options">';
    q.options.forEach(function (opt, i) {
      var selected = answer.selected === i ? ' quiz-option--selected' : '';
      var optImg = q.option_images && q.option_images[i] ? q.option_images[i] : null;
      html +=
        '<button class="quiz-option' + selected + '" data-index="' + i + '">' +
        '<span class="quiz-option__letter">' + LETTERS[i] + '</span>' +
        (optImg ? '<img src="' + optImg + '" alt="" class="quiz-option__img" loading="lazy">' : '') +
        '<span class="quiz-option__text">' + escapeHtml(opt) + '</span>' +
        '</button>';
    });
    html += '</div>';
    return html;
  }

  function _buildNavHtml(currentIndex, total) {
    var html =
      '<div style="display: flex; justify-content: space-between;">' +
      '<button class="btn btn--outline" id="quiz-prev" ' +
      (currentIndex === 0 ? 'disabled style="opacity: 0.4; cursor: not-allowed;"' : '') +
      '>上一题</button>' +
      '<span id="quiz-next-container">';

    if (currentIndex < total - 1) {
      html += '<button class="btn btn--primary" id="quiz-next">下一题</button>';
    } else {
      html += '<button class="btn btn--primary" id="quiz-review">查看答案</button>';
    }
    html += '</span></div>';
    return html;
  }

  function _bindQuestionEvents(answer) {
    // 选项点击
    CONTAINER.querySelectorAll('.quiz-option').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var idx = parseInt(this.getAttribute('data-index'), 10);
        selectOption(idx);
      });
    });

    // 上一题
    var prevBtn = document.getElementById('quiz-prev');
    if (prevBtn && state.currentIndex > 0) {
      prevBtn.addEventListener('click', function () {
        state.currentIndex--;
        render();
      });
    }

    // 下一题 / 查看答案
    var nextBtn = document.getElementById('quiz-next');
    var reviewBtn = document.getElementById('quiz-review');
    if (nextBtn) {
      nextBtn.addEventListener('click', function () {
        if (answer.selected === null) {
          alert('请先选择一个选项');
          return;
        }
        state.currentIndex++;
        render();
      });
    }
    if (reviewBtn) {
      reviewBtn.addEventListener('click', function () {
        if (answer.selected === null) {
          alert('请先选择一个选项');
          return;
        }
        state.phase = 'reviewing';
        render();
      });
    }
  }

  function renderQuestion() {
    var q = state.questions[state.currentIndex];
    var answer = state.answers[state.currentIndex];
    var total = state.questions.length;
    var current = state.currentIndex + 1;

    var html =
      _buildProgressHtml(current, total) +
      '<div class="quiz-question">' +
      (q.image_url ? '<img src="' + q.image_url + '" alt="' + escapeHtml(q.question) + '" class="quiz-question__image">' : '') +
      '<h2 class="quiz-question__text">' + escapeHtml(q.question) + '</h2>' +
      _buildOptionsHtml(q, answer) +
      '</div>' +
      _buildNavHtml(state.currentIndex, total);

    CONTAINER.innerHTML = html;
    _bindQuestionEvents(answer);
  }

  function selectOption(index) {
    state.answers[state.currentIndex].selected = index;
    // 重新渲染当前问题以更新样式
    renderQuestion();
  }

  function _buildReviewItemHtml(q, qi, answer) {
    var html =
      '<div class="quiz-review__item">' +
      (q.image_url ? '<img src="' + q.image_url + '" alt="' + escapeHtml(q.question) + '" class="quiz-review__image">' : '') +
      '<div class="quiz-review__question">' + (qi + 1) + '. ' + escapeHtml(q.question) + '</div>';

    html += '<div class="quiz-review__options">';

    q.options.forEach(function (opt, oi) {
      var selected = answer.selected === oi ? ' quiz-review__option--selected' : '';
      var optImg = q.option_images && q.option_images[oi] ? q.option_images[oi] : null;
      html +=
        '<button class="quiz-review__option' + selected + '" data-q="' + qi + '" data-o="' + oi + '">' +
        (optImg ? '<img src="' + optImg + '" alt="" class="quiz-review__option-img" loading="lazy">' : '') +
        '<span>' + LETTERS[oi] + '. ' + escapeHtml(opt) + '</span>' +
        '</button>';
    });

    html += '</div></div>';
    return html;
  }

  function renderReview() {
    var html =
      '<div class="quiz-review">' +
      '<h2 style="font-size: var(--text-xl); font-weight: 700; margin-bottom: var(--space-6);">✏️ 回顾你的答案</h2>';

    state.questions.forEach(function (q, qi) {
      var answer = state.answers[qi];
      html += _buildReviewItemHtml(q, qi, answer);
    });

    html +=
      '<div style="display: flex; gap: var(--space-3); justify-content: center; margin-top: var(--space-6);">' +
      '<button class="btn btn--outline" id="quiz-back">返回修改</button>' +
      '<button class="btn btn--primary" id="quiz-submit">提交答案</button>' +
      '</div></div>';

    CONTAINER.innerHTML = html;

    // 可点击修改选项
    CONTAINER.querySelectorAll('.quiz-review__option').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var qIdx = parseInt(this.getAttribute('data-q'), 10);
        var oIdx = parseInt(this.getAttribute('data-o'), 10);

        // 取消同题其他选项的选中状态
        CONTAINER.querySelectorAll('.quiz-review__option[data-q="' + qIdx + '"]').forEach(function (el) {
          el.classList.remove('quiz-review__option--selected');
        });
        this.classList.add('quiz-review__option--selected');
        state.answers[qIdx].selected = oIdx;
      });
    });

    document.getElementById('quiz-back').addEventListener('click', function () {
      state.phase = 'playing';
      // 找到第一个未答的题，或回到第一题
      var firstUnanswered = state.answers.findIndex(function (a) { return a.selected === null; });
      state.currentIndex = firstUnanswered >= 0 ? firstUnanswered : 0;
      render();
    });

    document.getElementById('quiz-submit').addEventListener('click', submitQuiz);
  }

  function submitQuiz() {
    if (state.submitting) return;
    state.submitting = true;

    // 检查是否有未回答的题
    var unanswered = state.answers.some(function (a) { return a.selected === null; });
    if (unanswered) {
      if (!confirm('还有题目未作答，确定要提交吗？')) {
        state.submitting = false;
        return;
      }
    }

    var submitBtn = document.getElementById('quiz-submit');
    if (submitBtn) {
      submitBtn.textContent = '提交中...';
      submitBtn.disabled = true;
    }

    var payload = {
      answers: state.answers.map(function (a) {
        return { q_id: a.qId, selected: a.selected === null ? -1 : a.selected };
      }),
    };

    fetch('/quiz/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(function (res) {
        if (!res.ok) throw new Error('提交失败');
        return res.json();
      })
      .then(function (data) {
        state.results = data;
        state.phase = 'results';
        state.submitting = false;
        saveBestScore(data.percentage);
        render();
      })
      .catch(function (err) {
        alert('提交失败：' + err.message + '。请重试。');
        state.submitting = false;
        if (submitBtn) {
          submitBtn.textContent = '提交答案';
          submitBtn.disabled = false;
        }
      });
  }

  function _buildScoreCircleHtml(data) {
    var scoreDeg = (data.percentage / 100) * 360;
    return (
      '<div class="score-circle" style="--score-deg: ' + scoreDeg + 'deg;">' +
      '<div class="score-circle__inner">' +
      '<span class="score-circle__number">' + data.percentage + '%</span>' +
      '<span class="score-circle__label">' + data.score + ' / ' + data.total + '</span>' +
      '</div></div>'
    );
  }

  function _buildResultDetailHtml(data) {
    // 建立 question_id -> option_images 的映射
    var qOptMap = {};
    state.questions.forEach(function (q) {
      qOptMap[q.id] = q.option_images || null;
    });

    var html = '<div class="result-detail">';
    data.details.forEach(function (item) {
      var icon = item.is_correct ? '✅' : '❌';
      var correctLabel = LETTERS[item.correct_index];
      var selectedLabel = item.selected >= 0 ? LETTERS[item.selected] : '未作答';
      var optImages = qOptMap[item.q_id] || null;

      html +=
        '<div class="result-item">' +
        '<span class="result-item__icon">' + icon + '</span>' +
        '<div class="result-item__content">' +
        '<div class="result-item__question">' + escapeHtml(item.question) + '</div>' +
        '<div class="result-item__options">';

      item.options.forEach(function (opt, oi) {
        var isCorrect = oi === item.correct_index;
        var isSelected = oi === item.selected;
        var optImg = optImages && optImages[oi] ? optImages[oi] : null;
        html +=
          '<div class="result-item__option' +
          (isCorrect ? ' result-item__option--correct' : '') +
          (isSelected && !isCorrect ? ' result-item__option--wrong' : '') +
          '">' +
          (optImg ? '<img src="' + optImg + '" alt="" class="result-item__option-img" loading="lazy">' : '') +
          '<span>' + LETTERS[oi] + '. ' + escapeHtml(opt) + '</span>' +
          '</div>';
      });

      html += '</div>' +
        '<div class="result-item__answer">' +
        '你的答案: <strong>' + selectedLabel + '</strong>' +
        (!item.is_correct ? ' | 正确答案: <strong style="color: #6b9e7a;">' + correctLabel + '</strong>' : '') +
        '</div>';

      if (item.explanation) {
        html += '<div class="result-item__explanation">💡 ' + escapeHtml(item.explanation) + '</div>';
      }

      html += '</div></div>';
    });
    html += '</div>';
    return html;
  }

  function renderResults() {
    var data = state.results;
    if (!data) {
      CONTAINER.innerHTML = '<div class="empty-state"><p>结果数据丢失，请重新测验。</p></div>';
      return;
    }

    var msg = getMessage(data.percentage);

    var html =
      '<div class="quiz-result">' +
      _buildScoreCircleHtml(data) +
      '<h2 style="font-size: var(--text-xl); font-weight: 700; margin-bottom: var(--space-2);">' + escapeHtml(msg.text) + '</h2>' +
      (data.details ? _buildResultDetailHtml(data) : '') +
      '<div style="margin-top: var(--space-8); display: flex; gap: var(--space-3); justify-content: center;">' +
      '<button class="btn btn--primary" id="quiz-play-again">再来一次</button>' +
      '<a href="/quiz/results" class="btn btn--outline">查看记录</a>' +
      '</div></div>';

    CONTAINER.innerHTML = html;

    document.getElementById('quiz-play-again').addEventListener('click', function () {
      state.phase = 'welcome';
      render();
    });
  }

  // ==================== 启动 ====================
  render();

  // 浏览器关闭/刷新警告
  window.addEventListener('beforeunload', function (e) {
    if (state.phase === 'playing' || state.phase === 'reviewing') {
      e.preventDefault();
      e.returnValue = '';
    }
  });

  // ==================== HTML 转义 ====================
  function escapeHtml(text) {
    if (typeof text !== 'string') return String(text);
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
  }

})();
