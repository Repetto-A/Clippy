"use client"

import { createContext, useContext, useState, type ReactNode } from "react"

export interface MediaFile {
  id: string
  file: File
  type: "video" | "image" | "audio"
  title: string
  size: string
  duration?: string
  thumbnail: string
  dateAdded: string
  url: string // Object URL for preview
}

interface MediaContextType {
  mediaFiles: MediaFile[]
  addMediaFile: (file: File) => Promise<{ success: boolean; error?: string }>
  removeMediaFile: (id: string) => void
  getMediaFile: (id: string) => MediaFile | undefined
}

const MediaContext = createContext<MediaContextType | undefined>(undefined)

export function MediaProvider({ children }: { children: ReactNode }) {
  const [mediaFiles, setMediaFiles] = useState<MediaFile[]>([])

  const validateFileSize = (file: File): { valid: boolean; error?: string } => {
    const maxSizes = {
      video: 5 * 1024 * 1024, // 5MB
      image: 1 * 1024 * 1024, // 1MB
      audio: 2 * 1024 * 1024, // 2MB
    }

    let fileType: "video" | "image" | "audio"
    if (file.type.startsWith("video/")) {
      fileType = "video"
    } else if (file.type.startsWith("image/")) {
      fileType = "image"
    } else if (file.type.startsWith("audio/")) {
      fileType = "audio"
    } else {
      return { valid: false, error: "Unsupported file type" }
    }

    if (file.size > maxSizes[fileType]) {
      const maxSizeMB = maxSizes[fileType] / (1024 * 1024)
      return {
        valid: false,
        error: `${fileType} files must be smaller than ${maxSizeMB}MB. Your file is ${(file.size / (1024 * 1024)).toFixed(1)}MB`,
      }
    }

    return { valid: true }
  }

  const addMediaFile = async (file: File): Promise<{ success: boolean; error?: string }> => {
    const validation = validateFileSize(file)
    if (!validation.valid) {
      return { success: false, error: validation.error }
    }

    try {
      const url = URL.createObjectURL(file)
      let type: "video" | "image" | "audio"

      if (file.type.startsWith("video/")) {
        type = "video"
      } else if (file.type.startsWith("image/")) {
        type = "image"
      } else {
        type = "audio"
      }

      let thumbnail = "/placeholder.svg?height=120&width=160&query=" + encodeURIComponent(file.name)
      if (type === "image") {
        thumbnail = url // Use the image itself as thumbnail
      }

      const mediaFile: MediaFile = {
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        file,
        type,
        title: file.name,
        size: (file.size / (1024 * 1024)).toFixed(1) + " MB",
        duration: type === "video" ? "0:00" : undefined,
        thumbnail,
        dateAdded: new Date().toISOString().split("T")[0],
        url,
      }

      setMediaFiles((prev) => [mediaFile, ...prev])
      return { success: true }
    } catch (error) {
      return { success: false, error: "Failed to process file" }
    }
  }

  const removeMediaFile = (id: string) => {
    setMediaFiles((prev) => {
      const fileToRemove = prev.find((f) => f.id === id)
      if (fileToRemove) {
        URL.revokeObjectURL(fileToRemove.url)
      }
      return prev.filter((f) => f.id !== id)
    })
  }

  const getMediaFile = (id: string) => {
    return mediaFiles.find((f) => f.id === id)
  }

  return (
    <MediaContext.Provider
      value={{
        mediaFiles,
        addMediaFile,
        removeMediaFile,
        getMediaFile,
      }}
    >
      {children}
    </MediaContext.Provider>
  )
}

export function useMedia() {
  const context = useContext(MediaContext)
  if (context === undefined) {
    throw new Error("useMedia must be used within a MediaProvider")
  }
  return context
}
