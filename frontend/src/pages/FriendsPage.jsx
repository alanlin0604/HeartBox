import { useState } from 'react'
import { useLang } from '../context/LanguageContext'
import PageTransition from '../components/PageTransition'
import FriendsList from '../components/friends/FriendsList'
import SharedWithMe from '../components/friends/SharedWithMe'
import FriendsActivity from '../components/friends/FriendsActivity'

export default function FriendsPage() {
  const { t } = useLang()
  const [activeTab, setActiveTab] = useState('friends')

  const tabs = [
    { id: 'friends', label: t('friends.myFriends'), icon: UsersIcon },
    { id: 'shared', label: t('friends.sharedWithMe'), icon: ShareIcon },
    { id: 'activity', label: t('friends.activity.title'), icon: ActivityIcon },
  ]

  return (
    <PageTransition>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6 bg-gradient-to-r from-green-400 to-emerald-500 bg-clip-text text-transparent">
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
                  ? 'bg-green-500/20 text-green-400'
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
          {activeTab === 'shared' && <SharedWithMe />}
          {activeTab === 'activity' && <FriendsActivity />}
        </div>
      </div>
    </PageTransition>
  )
}

// SVG Icons
function UsersIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
      <circle cx="9" cy="7" r="4"/>
      <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
      <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
    </svg>
  )
}

function ShareIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="18" cy="5" r="3"/>
      <circle cx="6" cy="12" r="3"/>
      <circle cx="18" cy="19" r="3"/>
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
      <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
    </svg>
  )
}

function ActivityIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  )
}
