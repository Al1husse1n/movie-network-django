// Simple front-end logic for posting and interacting with tweets
const timeline = document.getElementById('timeline');
const template = document.getElementById('tweetTemplate');
const postBtn = document.getElementById('postBtn');
const input = document.getElementById('tweetInput');
const charCount = document.getElementById('charCount');
const composeBtn = document.getElementById('composeBtn');

// initial sample tweets
// changed: removed automatic insertion of initial sample tweets so nothing is injected on load

function renderTweet(data){
  const el = template.content.cloneNode(true);
  el.querySelector('.t-text').textContent = data.text;
  el.querySelector('.count').textContent = data.likes;
  const likeBtn = el.querySelector('.icon.like');
  const rtBtn = el.querySelector('.icon.retweet');
  const replyBtn = el.querySelector('.icon.reply');

  likeBtn.addEventListener('click', () => {
    data.likes++;
    likeBtn.querySelector('.count').textContent = data.likes;
    likeBtn.classList.toggle('active');
  });

  rtBtn.addEventListener('click', () => {
    data.rts = (data.rts || 0) + 1;
    rtBtn.querySelector('.count').textContent = data.rts;
  });

  replyBtn.addEventListener('click', () => {
    data.replies = (data.replies || 0) + 1;
    replyBtn.querySelector('.count').textContent = data.replies;
    alert('Reply UI not implemented in this demo — replace with modal if you want.');
  });

  timeline.prepend(el);
}

// changed: do not inject any initial tweets here
// if server rendered posts exist they will show; otherwise timeline stays empty

postBtn.addEventListener('click', () => {
  const text = input.value.trim();
  if(!text) return;
  const tweet = {text, likes: 0, rts: 0, replies: 0};
  renderTweet(tweet);
  input.value = '';
  charCount.textContent = input.maxLength;
});

input.addEventListener('input', () => {
  const remaining = input.maxLength - input.value.length;
  charCount.textContent = remaining;
  if(remaining < 0) charCount.classList.add('over');
  else charCount.classList.remove('over');
});

composeBtn.addEventListener('click', () => {
  document.getElementById('composer').scrollIntoView({behavior:'smooth'});
  input.focus();
});

// Simple persistence using localStorage (optional)
window.addEventListener('beforeunload', () => {
  // gather tweets from DOM for persistence in a tiny format
  const tweets = [];
  document.querySelectorAll('#timeline .tweet').forEach(t => {
    tweets.push({text: t.querySelector('.t-text').textContent});
  });
  localStorage.setItem('greenbird_tweets', JSON.stringify(tweets));
});

window.addEventListener('load', () => {
  const data = JSON.parse(localStorage.getItem('greenbird_tweets') || 'null');
  if(data && data.length){
    // remove any placeholder content then render persisted tweets
    timeline.innerHTML = '';
    data.forEach(d => renderTweet({text:d.text, likes:0,rts:0,replies:0}));
  }
});
