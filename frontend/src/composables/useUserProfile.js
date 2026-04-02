import { ref } from "vue"

import { userHttp } from "../lib/http"
import { getUserInfo, getUserToken, setUserInfo } from "../lib/session"

export function useUserProfile() {
  const user = ref(getUserInfo())
  const loading = ref(false)

  async function refreshUser() {
    if (!getUserToken()) {
      user.value = getUserInfo()
      loading.value = false
      return null
    }
    loading.value = true
    try {
      const data = await userHttp.get("/users/me")
      user.value = data
      setUserInfo(data)
    } finally {
      loading.value = false
    }
  }

  return {
    user,
    loading,
    refreshUser,
  }
}
