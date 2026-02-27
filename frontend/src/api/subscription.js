import api from './axios'

export const getPlans = () => api.get('/subscriptions/plans/')
export const getMySubscription = () => api.get('/subscriptions/me/')
export const subscribe = (planId) => api.post('/subscriptions/me/', { plan: planId })
