import { social, FriendshipData, ClubData, NotificationData, FeedItem } from "../api";
import { getUsername } from "../auth";

export function renderSocial(): string {
  return `
    <div class="social-page">
      <div class="social-tabs">
        <button class="social-tab active" data-tab="feed">Feed</button>
        <button class="social-tab" data-tab="friends">Friends</button>
        <button class="social-tab" data-tab="clubs">Book Clubs</button>
        <button class="social-tab" data-tab="notifications">
          Notifications <span id="notif-badge" class="notif-badge hidden"></span>
        </button>
      </div>
      <div id="social-content" class="social-content">
        <div class="loading">Loading...</div>
      </div>
    </div>
  `;
}

document.addEventListener("page:mounted", (e) => {
  const detail = (e as CustomEvent).detail;
  if (detail?.name !== "social") return;

  const tabs = document.querySelectorAll(".social-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const tabName = (tab as HTMLElement).dataset.tab!;
      loadTab(tabName);
    });
  });

  // Load unread count for badge
  social.unreadCount().then(({ count }) => {
    const badge = document.getElementById("notif-badge");
    if (badge && count > 0) {
      badge.textContent = String(count);
      badge.classList.remove("hidden");
    }
  }).catch(() => {});

  loadTab("feed");
});

async function loadTab(tab: string) {
  const container = document.getElementById("social-content");
  if (!container) return;
  container.innerHTML = '<div class="loading">Loading...</div>';

  try {
    switch (tab) {
      case "feed": await loadFeed(container); break;
      case "friends": await loadFriends(container); break;
      case "clubs": await loadClubs(container); break;
      case "notifications": await loadNotifications(container); break;
    }
  } catch (err) {
    container.innerHTML = `<div class="social-empty">Failed to load. ${(err as Error).message}</div>`;
  }
}

// ===================== FEED =====================

async function loadFeed(container: HTMLElement) {
  const feed = await social.feed();
  if (feed.length === 0) {
    container.innerHTML = `
      <div class="social-empty">
        <p>No activity yet. Add friends to see their reading activity here.</p>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="feed-list">
      ${feed.map(renderFeedItem).join("")}
    </div>`;
}

function renderFeedItem(item: FeedItem): string {
  const time = timeAgo(item.timestamp);
  const initial = item.user.username.charAt(0).toUpperCase();

  if (item.type === "book_finished") {
    return `
      <div class="feed-item">
        <div class="feed-avatar">${initial}</div>
        <div class="feed-body">
          <strong>${esc(item.user.username)}</strong> finished reading
          <em>${esc(item.book_title ?? "")}</em>
          <span class="feed-time">${time}</span>
        </div>
      </div>`;
  }
  if (item.type === "shared_highlight") {
    return `
      <div class="feed-item">
        <div class="feed-avatar">${initial}</div>
        <div class="feed-body">
          <strong>${esc(item.user.username)}</strong> highlighted in
          <em>${esc(item.book_title ?? "")}</em>
          <blockquote class="feed-quote">"${esc(item.text ?? "")}"</blockquote>
          <span class="feed-time">${time}</span>
        </div>
      </div>`;
  }
  return "";
}

// ===================== FRIENDS =====================

async function loadFriends(container: HTMLElement) {
  const [friends, requests] = await Promise.all([
    social.friends(),
    social.friendRequests(),
  ]);

  container.innerHTML = `
    <div class="social-section">
      <div class="social-section-header">
        <h3>Add Friend</h3>
      </div>
      <div class="friend-search-row">
        <input type="text" id="friend-search-input" class="input" placeholder="Search by username..." />
        <button id="friend-search-btn" class="btn btn-primary">Search</button>
      </div>
      <div id="friend-search-results"></div>
    </div>

    ${requests.length > 0 ? `
      <div class="social-section">
        <h3>Friend Requests (${requests.length})</h3>
        <div class="friend-list">
          ${requests.map((r) => `
            <div class="friend-card">
              <div class="friend-avatar">${r.user.username.charAt(0).toUpperCase()}</div>
              <span class="friend-name">${esc(r.user.username)}</span>
              <button class="btn btn-sm btn-primary" data-accept="${r.id}">Accept</button>
              <button class="btn btn-sm btn-danger" data-reject="${r.id}">Decline</button>
            </div>
          `).join("")}
        </div>
      </div>
    ` : ""}

    <div class="social-section">
      <h3>Friends (${friends.length})</h3>
      ${friends.length === 0 ? '<p class="social-muted">No friends yet. Search for users above.</p>' : `
        <div class="friend-list">
          ${friends.map((f) => `
            <div class="friend-card">
              <div class="friend-avatar">${f.user.username.charAt(0).toUpperCase()}</div>
              <span class="friend-name">${esc(f.user.username)}</span>
              <button class="btn btn-sm" data-view-shelf="${f.user.id}" data-username="${esc(f.user.username)}">View Shelf</button>
              <button class="btn btn-sm btn-danger" data-remove-friend="${f.id}">Remove</button>
            </div>
          `).join("")}
        </div>
      `}
    </div>

    <div id="friend-shelf-modal" class="modal-overlay hidden">
      <div class="modal-content">
        <div class="modal-header">
          <h3 id="shelf-modal-title">Shelf</h3>
          <button class="modal-close" id="close-shelf-modal">&times;</button>
        </div>
        <div id="shelf-modal-body"></div>
      </div>
    </div>
  `;

  // Friend search
  const searchBtn = document.getElementById("friend-search-btn");
  const searchInput = document.getElementById("friend-search-input") as HTMLInputElement;
  searchBtn?.addEventListener("click", async () => {
    const q = searchInput?.value.trim();
    if (!q || q.length < 2) return;
    const results = await social.searchUsers(q);
    const resultsDiv = document.getElementById("friend-search-results");
    if (!resultsDiv) return;
    if (results.length === 0) {
      resultsDiv.innerHTML = '<p class="social-muted">No users found.</p>';
      return;
    }
    const existingIds = new Set(friends.map((f) => f.user.id));
    const pendingIds = new Set(requests.map((r) => r.user.id));
    resultsDiv.innerHTML = results.map((u) => {
      if (u.username === getUsername()) return "";
      const isFriend = existingIds.has(u.id);
      const isPending = pendingIds.has(u.id);
      return `
        <div class="friend-card">
          <div class="friend-avatar">${u.username.charAt(0).toUpperCase()}</div>
          <span class="friend-name">${esc(u.username)}</span>
          ${isFriend ? '<span class="social-muted">Already friends</span>' :
            isPending ? '<span class="social-muted">Pending</span>' :
            `<button class="btn btn-sm btn-primary" data-add-friend="${esc(u.username)}">Add Friend</button>`}
        </div>`;
    }).join("");

    resultsDiv.querySelectorAll("[data-add-friend]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const username = (btn as HTMLElement).dataset.addFriend!;
        try {
          await social.sendFriendRequest(username);
          (btn as HTMLElement).replaceWith(Object.assign(document.createElement("span"), { className: "social-muted", textContent: "Request sent" }));
        } catch (err) { alert((err as Error).message); }
      });
    });
  });

  searchInput?.addEventListener("keydown", (e) => { if (e.key === "Enter") searchBtn?.click(); });

  // Accept/reject friend requests
  container.querySelectorAll("[data-accept]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await social.acceptFriend(Number((btn as HTMLElement).dataset.accept));
      loadTab("friends");
    });
  });
  container.querySelectorAll("[data-reject]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await social.removeFriend(Number((btn as HTMLElement).dataset.reject));
      loadTab("friends");
    });
  });

  // Remove friend
  container.querySelectorAll("[data-remove-friend]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Remove this friend?")) return;
      await social.removeFriend(Number((btn as HTMLElement).dataset.removeFriend));
      loadTab("friends");
    });
  });

  // View shelf
  container.querySelectorAll("[data-view-shelf]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const userId = Number((btn as HTMLElement).dataset.viewShelf);
      const username = (btn as HTMLElement).dataset.username;
      const modal = document.getElementById("friend-shelf-modal");
      const title = document.getElementById("shelf-modal-title");
      const body = document.getElementById("shelf-modal-body");
      if (!modal || !body) return;
      if (title) title.textContent = `${username}'s Shelf`;
      body.innerHTML = '<div class="loading">Loading...</div>';
      modal.classList.remove("hidden");

      try {
        const shelf = await social.viewFriendShelf(userId);
        if (shelf.length === 0) {
          body.innerHTML = '<p class="social-muted">No books on shelf.</p>';
          return;
        }
        body.innerHTML = `<div class="shelf-grid">${shelf.map((b: any) => `
          <div class="shelf-book">
            <div class="shelf-book-cover" style="background-image: url('${b.cover_url || ""}')">
              ${!b.cover_url ? '<span class="shelf-book-initial">' + (b.title?.charAt(0) || "?") + '</span>' : ""}
            </div>
            <div class="shelf-book-info">
              <div class="shelf-book-title">${esc(b.title)}</div>
              <div class="shelf-book-author">${esc(b.author || "")}</div>
              <div class="shelf-book-status">${b.status} &middot; ${Math.round(b.progress * 100)}%</div>
            </div>
          </div>
        `).join("")}</div>`;
      } catch (err) {
        body.innerHTML = `<p class="social-muted">Could not load shelf.</p>`;
      }
    });
  });

  document.getElementById("close-shelf-modal")?.addEventListener("click", () => {
    document.getElementById("friend-shelf-modal")?.classList.add("hidden");
  });
}

// ===================== CLUBS =====================

async function loadClubs(container: HTMLElement) {
  const [myClubs, allClubs] = await Promise.all([
    social.clubs(),
    social.discoverClubs(),
  ]);

  const myClubIds = new Set(myClubs.map((c) => c.id));

  container.innerHTML = `
    <div class="social-section">
      <div class="social-section-header">
        <h3>Create Book Club</h3>
      </div>
      <div class="club-create-form">
        <input type="text" id="club-name" class="input" placeholder="Club name" />
        <input type="text" id="club-desc" class="input" placeholder="Description (optional)" />
        <button id="create-club-btn" class="btn btn-primary">Create Club</button>
      </div>
    </div>

    <div class="social-section">
      <h3>My Clubs (${myClubs.length})</h3>
      ${myClubs.length === 0 ? '<p class="social-muted">You haven\'t joined any clubs yet.</p>' :
        `<div class="club-list">${myClubs.map((c) => renderClubCard(c, true)).join("")}</div>`}
    </div>

    <div class="social-section">
      <h3>Discover Clubs</h3>
      ${allClubs.filter((c) => !myClubIds.has(c.id)).length === 0 ?
        '<p class="social-muted">No other clubs to discover.</p>' :
        `<div class="club-list">${allClubs.filter((c) => !myClubIds.has(c.id)).map((c) => renderClubCard(c, false)).join("")}</div>`}
    </div>

    <div id="club-detail-modal" class="modal-overlay hidden">
      <div class="modal-content modal-large">
        <div class="modal-header">
          <h3 id="club-detail-title">Club</h3>
          <button class="modal-close" id="close-club-modal">&times;</button>
        </div>
        <div id="club-detail-body"></div>
      </div>
    </div>
  `;

  // Create club
  document.getElementById("create-club-btn")?.addEventListener("click", async () => {
    const name = (document.getElementById("club-name") as HTMLInputElement)?.value.trim();
    const desc = (document.getElementById("club-desc") as HTMLInputElement)?.value.trim();
    if (!name) return;
    try {
      await social.createClub({ name, description: desc || undefined });
      loadTab("clubs");
    } catch (err) { alert((err as Error).message); }
  });

  // Join club
  container.querySelectorAll("[data-join-club]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await social.joinClub(Number((btn as HTMLElement).dataset.joinClub));
      loadTab("clubs");
    });
  });

  // Leave club
  container.querySelectorAll("[data-leave-club]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Leave this club?")) return;
      await social.leaveClub(Number((btn as HTMLElement).dataset.leaveClub));
      loadTab("clubs");
    });
  });

  // Delete club
  container.querySelectorAll("[data-delete-club]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Delete this club permanently?")) return;
      await social.deleteClub(Number((btn as HTMLElement).dataset.deleteClub));
      loadTab("clubs");
    });
  });

  // Open club detail (discussions)
  container.querySelectorAll("[data-open-club]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const clubId = Number((btn as HTMLElement).dataset.openClub);
      const club = myClubs.find((c) => c.id === clubId);
      if (club) openClubDetail(club);
    });
  });

  document.getElementById("close-club-modal")?.addEventListener("click", () => {
    document.getElementById("club-detail-modal")?.classList.add("hidden");
  });
}

function renderClubCard(club: ClubData, isMember: boolean): string {
  const username = getUsername();
  const isCreator = club.creator === username;
  return `
    <div class="club-card">
      <div class="club-card-header">
        <h4>${esc(club.name)}</h4>
        <span class="club-members">${club.member_count} member${club.member_count !== 1 ? "s" : ""}</span>
      </div>
      ${club.description ? `<p class="club-desc">${esc(club.description)}</p>` : ""}
      ${club.book_title ? `<p class="club-book">Reading: <em>${esc(club.book_title)}</em></p>` : ""}
      ${club.target_date ? `<p class="club-target">Target: ${new Date(club.target_date).toLocaleDateString()}</p>` : ""}
      <div class="club-actions">
        ${isMember ? `
          <button class="btn btn-sm" data-open-club="${club.id}">Discussions</button>
          <button class="btn btn-sm btn-danger" data-leave-club="${club.id}">Leave</button>
          ${isCreator ? `<button class="btn btn-sm btn-danger" data-delete-club="${club.id}">Delete</button>` : ""}
        ` : `
          <button class="btn btn-sm btn-primary" data-join-club="${club.id}">Join</button>
        `}
      </div>
    </div>`;
}

async function openClubDetail(club: ClubData) {
  const modal = document.getElementById("club-detail-modal");
  const title = document.getElementById("club-detail-title");
  const body = document.getElementById("club-detail-body");
  if (!modal || !body) return;
  if (title) title.textContent = club.name;
  body.innerHTML = '<div class="loading">Loading...</div>';
  modal.classList.remove("hidden");

  try {
    const discussions = await social.clubDiscussions(club.id);
    body.innerHTML = `
      <div class="club-discussions">
        <div class="disc-create">
          <input type="text" id="disc-title" class="input" placeholder="Discussion title" />
          <textarea id="disc-body" class="input" placeholder="What's on your mind?" rows="3"></textarea>
          <button id="create-disc-btn" class="btn btn-primary">Post</button>
        </div>
        <div id="disc-list">
          ${discussions.length === 0 ? '<p class="social-muted">No discussions yet. Start one above.</p>' :
            discussions.map((d) => `
              <div class="disc-card" data-disc-id="${d.id}">
                <div class="disc-header">
                  <strong>${esc(d.user.username)}</strong>
                  <span class="disc-time">${timeAgo(d.created_at)}</span>
                </div>
                <h4 class="disc-title">${esc(d.title)}</h4>
                ${d.body ? `<p class="disc-body">${esc(d.body)}</p>` : ""}
                <button class="btn btn-sm" data-toggle-replies="${d.id}">${d.reply_count} repl${d.reply_count !== 1 ? "ies" : "y"}</button>
                <div class="disc-replies hidden" id="replies-${d.id}"></div>
              </div>
            `).join("")}
        </div>
      </div>`;

    document.getElementById("create-disc-btn")?.addEventListener("click", async () => {
      const t = (document.getElementById("disc-title") as HTMLInputElement)?.value.trim();
      const b = (document.getElementById("disc-body") as HTMLTextAreaElement)?.value.trim();
      if (!t) return;
      await social.createDiscussion(club.id, t, b || undefined);
      openClubDetail(club);
    });

    body.querySelectorAll("[data-toggle-replies]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const discId = Number((btn as HTMLElement).dataset.toggleReplies);
        const repliesDiv = document.getElementById(`replies-${discId}`);
        if (!repliesDiv) return;
        if (!repliesDiv.classList.contains("hidden")) {
          repliesDiv.classList.add("hidden");
          return;
        }
        repliesDiv.classList.remove("hidden");
        repliesDiv.innerHTML = '<div class="loading">Loading...</div>';
        const replies = await social.discussionReplies(discId);
        repliesDiv.innerHTML = `
          ${replies.map((r) => `
            <div class="reply">
              <strong>${esc(r.user.username)}</strong>
              <span class="disc-time">${timeAgo(r.created_at)}</span>
              <p>${esc(r.body)}</p>
            </div>
          `).join("")}
          <div class="reply-form">
            <input type="text" class="input reply-input" placeholder="Write a reply..." data-reply-disc="${discId}" />
            <button class="btn btn-sm btn-primary reply-send" data-send-reply="${discId}">Send</button>
          </div>`;

        repliesDiv.querySelector(`[data-send-reply="${discId}"]`)?.addEventListener("click", async () => {
          const input = repliesDiv.querySelector(`[data-reply-disc="${discId}"]`) as HTMLInputElement;
          const text = input?.value.trim();
          if (!text) return;
          await social.addReply(discId, text);
          // Reload replies
          btn.dispatchEvent(new Event("click"));
          btn.dispatchEvent(new Event("click"));
        });
      });
    });

  } catch (err) {
    body.innerHTML = `<p class="social-muted">Failed to load discussions.</p>`;
  }
}

// ===================== NOTIFICATIONS =====================

async function loadNotifications(container: HTMLElement) {
  const notifs = await social.notifications();

  container.innerHTML = `
    <div class="social-section">
      <div class="social-section-header">
        <h3>Notifications</h3>
        ${notifs.some((n) => !n.is_read) ? '<button id="mark-all-read" class="btn btn-sm">Mark all read</button>' : ""}
      </div>
      ${notifs.length === 0 ? '<p class="social-muted">No notifications.</p>' : `
        <div class="notif-list">
          ${notifs.map((n) => `
            <div class="notif-item ${n.is_read ? "" : "notif-unread"}" data-notif-id="${n.id}">
              <div class="notif-icon">${notifIcon(n.type)}</div>
              <div class="notif-body">
                <p>${esc(n.message)}</p>
                <span class="notif-time">${timeAgo(n.created_at)}</span>
              </div>
            </div>
          `).join("")}
        </div>
      `}
    </div>`;

  document.getElementById("mark-all-read")?.addEventListener("click", async () => {
    await social.markAllRead();
    const badge = document.getElementById("notif-badge");
    if (badge) badge.classList.add("hidden");
    loadTab("notifications");
  });

  container.querySelectorAll(".notif-unread").forEach((el) => {
    el.addEventListener("click", async () => {
      const id = Number((el as HTMLElement).dataset.notifId);
      await social.markRead(id);
      el.classList.remove("notif-unread");
    });
  });
}

function notifIcon(type: string): string {
  switch (type) {
    case "friend_request": return "👤";
    case "friend_accepted": return "🤝";
    case "group_invite": return "📖";
    case "club_invite": return "📚";
    case "club_discussion": return "💬";
    case "highlight_comment": return "✍️";
    case "book_finished": return "🎉";
    default: return "🔔";
  }
}

// ===================== UTILS =====================

function esc(s: string): string {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}
