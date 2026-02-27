import api from '../api/axios'

export async function subscribeToPush() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return false

  try {
    const registration = await navigator.serviceWorker.ready
    const vapidPublicKey = import.meta.env.VITE_VAPID_PUBLIC_KEY
    if (!vapidPublicKey) return false

    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
    })

    const json = subscription.toJSON()
    await api.post('/push/subscribe/', {
      endpoint: json.endpoint,
      keys: json.keys,
    })
    return true
  } catch {
    return false
  }
}

export async function unsubscribePush() {
  try {
    const registration = await navigator.serviceWorker.ready
    const subscription = await registration.pushManager.getSubscription()
    if (subscription) {
      await api.delete('/push/subscribe/', { data: { endpoint: subscription.endpoint } })
      await subscription.unsubscribe()
    }
    return true
  } catch {
    return false
  }
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}
