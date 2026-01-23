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
                    card.innerHTML = `
                    <div class="community-name">${communityName}</div>
                    <div class="community-info">
                    👥 Admin ${community.admin ?? '—'}<br>
                    🛡️ ${community.member_amount ?? 0} members
                    </div>
                    <span class="badge ${community.visibility ?? ''}">
                     ${community.visibility.toUpperCase() ?? ''}
                    </span>
                     `;
                    container.appendChild(card);
                    container.style.display = "grid";
                    placeholderText.style.display = "none";
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
