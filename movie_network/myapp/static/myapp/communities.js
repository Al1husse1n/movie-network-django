const container = document.getElementById("communityResults");
const searchInput = document.getElementById("searchInput");
const searchBtn = document.getElementById("searchBtn");
const placeholderText = document.getElementById("placeholderText");


searchBtn.addEventListener("click", () => {
  const query = searchInput.value.trim();

  if (!query) {
    placeholderText.textContent = "⚠️ Please enter a search term";
    placeholderText.style.display = "block";
    container.style.display = "none";
    return;
  }
  container.innerHTML = "";
    fetch(`/getcommunity/${query}`)
    .then(response =>{
        return response.json()
        .then(parsedResponse =>{
            if(response.status === 400){
                alert(parsedResponse.error);
            }
            else if(response.status === 404){
                placeholderText.textContent = "❌ No communities found";
                placeholderText.style.display = "block";
                container.style.display = "none";
            }
            else if(response.status === 500){
                placeholderText.textContent = "⚠️ Something happened, please try again";
                console.error(parsedResponse.error);
                placeholderText.style.display = "block";
                container.style.display = "none";
            }
            else{
                                for(let communityName in parsedResponse){
                                        const community = parsedResponse[communityName];
                                        const card = document.createElement("div");
                                        card.className = "community-card";

                                        // derive members array safely
                                        let members = [];
                                        if (Array.isArray(community.members)) members = community.members;
                                        else if (Array.isArray(community.member_list)) members = community.member_list;
                                        else if (Array.isArray(community.member_usernames)) members = community.member_usernames;
                                        else if (Array.isArray(community.sample_members)) members = community.sample_members;

                                        const memberNames = members.map(m => typeof m === 'string' ? m : (m.username || m.name || m.display_name || 'member'));
                                        const membersText = memberNames.length ? memberNames.slice(0,3).join(', ') + (memberNames.length > 3 ? ' and more' : '') : 'No members yet — be the first!';

                                        const visibility = (community.visibility || '').toLowerCase();

                                        // decide if current user is a member
                                        const isMember = (typeof CURRENT_USER !== 'undefined') && memberNames.some(n => n === CURRENT_USER);
                                        const joinLabel = isMember ? 'Leave community' : (visibility === 'public' ? 'Join community' : 'Request to join');

                                        card.innerHTML = `
                                        <div class="community-name">${communityName}</div>
                                        <div class="community-info">
                                            👥 Admin: ${community.admin ?? '—'}<br>
                                            🛡️ ${community.member_amount ?? 0} members
                                        </div>
                                        <div class="community-members">Members: ${membersText}</div>
                                        <span class="badge ${visibility}">${(visibility || '').toUpperCase()}</span>
                                        <div class="community-actions">
                                            <button class="join-btn" data-id="${community.id ?? community.pk ?? ''}" data-visibility="${visibility}" data-member="${isMember}">${joinLabel}</button>
                                        </div>
                                         `;

                                        container.appendChild(card);
                                        container.style.display = "grid";
                                        placeholderText.style.display = "none";

                                        // attach join/request handler
                                        const btn = card.querySelector('.join-btn');
                                        if (btn) {
                                            btn.addEventListener('click', () => {
                                                const vis = btn.dataset.visibility;
                                                const cid = btn.dataset.id;
                                                const member = btn.dataset.member === 'true';
                                                if (member) {
                                                    // leaving
                                                    btn.textContent = 'Left';
                                                    btn.disabled = true;
                                                    btn.dataset.member = 'false';
                                                    btn.classList.add('left');
                                                    // TODO: call backend leave endpoint when ready
                                                    // fetch(`/communities/${cid}/leave/`, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '' } })
                                                } else {
                                                    // joining or requesting
                                                    if (vis === 'public') btn.textContent = 'Joined';
                                                    else btn.textContent = 'Request sent';
                                                    btn.disabled = true;
                                                    btn.dataset.member = 'true';
                                                    // TODO: call backend join/request endpoint when ready
                                                    // fetch(`/communities/${cid}/${vis === 'public' ? 'join' : 'request'}/`, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '' } })
                                                }
                                            });
                                        }
                                        console.log('community object:', community);
                                }
            }
        })
    })
    .catch(error =>{
        placeholderText.textContent = "⚠️ Something happened, please try again";
        console.error(error);
    })
});
