import { useState } from 'react'
import { useLang } from '../context/LanguageContext'
import PageTransition from '../components/PageTransition'
import FriendsList from '../components/friends/FriendsList'
import SharedWithMe from '../components/friends/SharedWithMe'
import SharedByMe from '../components/friends/SharedByMe'
import FriendsActivity from '../components/friends/FriendsActivity'
import FriendsLeaderboard from '../components/friends/FriendsLeaderboard'

export default function FriendsPage() {
  const { t } = useLang()
  const [activeTab, setActiveTab] = useState('friends')

  const tabs = [
    { id: 'friends', label: t('friends.myFriends'), icon: UsersIcon },
    { id: 'leaderboard', label: t('friends.leaderboard'), icon: TrophyIcon },
    { id: 'shared', label: t('friends.share.sharedWithMe'), icon: ShareIcon },
    { id: 'sharedByMe', label: t('friends.share.sharedByMe'), icon: SentIcon },
    { id: 'activity', label: t('friends.activity.title'), icon: ActivityIcon },
  ]

  return (
    <PageTransition>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6 bg-gradient-to-r from-orange-500 to-rose-500 bg-clip-text text-transparent">
          {t('friends.title')}
        </h1>

        {/* Tab Navigation */}
        <div className="glass-card p-1 mb-6 flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex-1 px-4 py-3 rounded-lg font-medium text-sm transition-all
                flex items-center justify-center gap-2
                ${activeTab === tab.id
                  ? 'bg-orange-500/20 text-orange-400'
                  : 'text-slate-400 hover:text-slate-300 hover:bg-white/5'
                }
              `}
            >
              <tab.icon />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="min-h-[400px]">
          {activeTab === 'friends' && <FriendsList />}
          {activeTab === 'leaderboard' && <FriendsLeaderboard />}
          {activeTab === 'shared' && <SharedWithMe />}
          {activeTab === 'sharedByMe' && <SharedByMe />}
          {activeTab === 'activity' && <FriendsActivity />}
        </div>
      </div>
    </PageTransition>
  )
}

// Tab icons — switched 2026-05-23 from inline stroke-currentColor SVGs
// to <img> at the new artwork set. Same shape as the previous components
// (zero-arg returning an icon element) so the tabs map call is untouched.
const tabIconImg = (src) => () => (
  <img src={src} alt="" aria-hidden="true" className="w-5 h-5 object-contain" />
)
const UsersIcon = tabIconImg('/icons/my-friends.svg')
const ShareIcon = tabIconImg('/icons/share.svg')
// Reuse share.svg for the "sent by me" tab — it's the same conceptual
// glyph (a fan-out) and we don't ship a separate sent-share icon yet.
const SentIcon = tabIconImg('/icons/share.svg')
const ActivityIcon = tabIconImg('/icons/activity.svg')
const TrophyIcon = tabIconImg('/icons/ranking.svg')
