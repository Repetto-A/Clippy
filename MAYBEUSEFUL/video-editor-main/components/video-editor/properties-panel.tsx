"use client"

import type React from "react"
import { useMedia } from "@/contexts/media-context"
import { toast } from "@/hooks/use-toast"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Slider } from "@/components/ui/slider"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Video,
  Volume2,
  Palette,
  Crop,
  RotateCw,
  Eye,
  Search,
  Download,
  Play,
  ImageIcon,
  Film,
  FolderOpen,
  Trash2,
  Upload,
} from "lucide-react"
import { useState, useRef } from "react"

function MediaPool() {
  const { mediaFiles, addMediaFile, removeMediaFile } = useMedia()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleUpload = () => {
    fileInputRef.current?.click()
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (files) {
      for (const file of Array.from(files)) {
        const result = await addMediaFile(file)
        if (result.success) {
          toast({
            title: "File uploaded successfully",
            description: `${file.name} has been added to your media pool`,
          })
        } else {
          toast({
            title: "Upload failed",
            description: result.error,
            variant: "destructive",
          })
        }
      }
    }
    event.target.value = ""
  }

  const handleDelete = (id: string) => {
    removeMediaFile(id)
    toast({
      title: "File removed",
      description: "Media file has been removed from your pool",
    })
  }

  const handleDragStart = (e: React.DragEvent, mediaFile: any) => {
    const dragData = {
      type: "media",
      mediaId: mediaFile.id,
      mediaType: mediaFile.type,
      title: mediaFile.title,
      duration: mediaFile.type === "video" ? 120 : mediaFile.type === "image" ? 60 : 180, // Default durations
    }
    e.dataTransfer.setData("application/json", JSON.stringify(dragData))
    e.dataTransfer.effectAllowed = "copy"
  }

  return (
    <ScrollArea className="h-full">
      <div className="space-y-4 p-1">
        {/* Upload Button with size limits info */}
        <div className="space-y-2">
          <Button onClick={handleUpload} className="w-full gap-2">
            <Upload className="h-4 w-4" />
            Upload Media Files
          </Button>

          <div className="text-xs text-muted-foreground text-center space-y-1">
            <div>Size limits: Videos ≤5MB, Images ≤1MB, Audio ≤2MB</div>
            <div>Supported: MP4, MOV, AVI, JPG, PNG, GIF, MP3, WAV</div>
          </div>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="video/*,image/*,audio/*"
          className="hidden"
          onChange={handleFileUpload}
        />

        {/* Media Stats */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="p-2 bg-muted rounded-lg">
            <div className="text-lg font-semibold">{mediaFiles.filter((m) => m.type === "video").length}</div>
            <div className="text-xs text-muted-foreground">Videos</div>
          </div>
          <div className="p-2 bg-muted rounded-lg">
            <div className="text-lg font-semibold">{mediaFiles.filter((m) => m.type === "image").length}</div>
            <div className="text-xs text-muted-foreground">Images</div>
          </div>
          <div className="p-2 bg-muted rounded-lg">
            <div className="text-lg font-semibold">{mediaFiles.filter((m) => m.type === "audio").length}</div>
            <div className="text-xs text-muted-foreground">Audio</div>
          </div>
        </div>

        {/* Media Grid */}
        <div className="space-y-2">
          {mediaFiles.map((item) => (
            <Card
              key={item.id}
              className="group cursor-grab active:cursor-grabbing"
              draggable
              onDragStart={(e) => handleDragStart(e, item)}
            >
              <CardContent className="p-3">
                <div className="flex gap-3">
                  {/* Thumbnail */}
                  <div className="relative w-16 h-12 rounded overflow-hidden bg-muted flex-shrink-0">
                    <img
                      src={item.thumbnail || "/placeholder.svg"}
                      alt={item.title}
                      className="w-full h-full object-cover"
                    />
                    {item.type === "video" && (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <Play className="h-4 w-4 text-white drop-shadow-lg" />
                      </div>
                    )}
                    {item.type === "audio" && (
                      <div className="absolute inset-0 flex items-center justify-center bg-muted">
                        <Volume2 className="h-4 w-4 text-muted-foreground" />
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between">
                      <div className="min-w-0 flex-1">
                        <h4 className="text-sm font-medium truncate">{item.title}</h4>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="outline" className="text-xs">
                            {item.type === "video" ? (
                              <>
                                <Film className="h-2 w-2 mr-1" />
                                {item.duration}
                              </>
                            ) : item.type === "audio" ? (
                              <>
                                <Volume2 className="h-2 w-2 mr-1" />
                                AUDIO
                              </>
                            ) : (
                              <>
                                <ImageIcon className="h-2 w-2 mr-1" />
                                IMG
                              </>
                            )}
                          </Badge>
                          <span className="text-xs text-muted-foreground">{item.size}</span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">Local Upload • {item.dateAdded}</p>
                        <p className="text-xs text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity">
                          Drag to timeline to add - make sure you add video track first         
                        </p>
                      </div>

                      {/* Actions */}
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button size="sm" variant="ghost" className="h-6 w-6 p-0">
                          <FolderOpen className="h-3 w-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 w-6 p-0 text-destructive hover:text-destructive"
                          onClick={() => handleDelete(item.id)}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {mediaFiles.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <FolderOpen className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No media files yet</p>
            <p className="text-xs">Upload files with size limits: Videos ≤5MB, Images ≤1MB, Audio ≤2MB</p>
          </div>
        )}
      </div>
    </ScrollArea>
  )
}

function MediaLibrary() {
  const [searchQuery, setSearchQuery] = useState("")
  const [activeCategory, setActiveCategory] = useState("all")

  // Mock data for demonstration - in real app, this would come from APIs
  const mockMedia = [
    {
      id: 1,
      type: "video",
      title: "Ocean Waves",
      duration: "0:15",
      thumbnail: "/ocean-waves.png",
      source: "Pexels",
    },
    { id: 2, type: "image", title: "Mountain Landscape", thumbnail: "/majestic-mountain-vista.png", source: "Pexels" },
    {
      id: 3,
      type: "video",
      title: "City Traffic",
      duration: "0:30",
      thumbnail: "/busy-city-intersection.png",
      source: "Pexels",
    },
    { id: 4, type: "image", title: "Abstract Pattern", thumbnail: "/abstract-geometric-flow.png", source: "Pexels" },
    {
      id: 5,
      type: "video",
      title: "Forest Walk",
      duration: "0:45",
      thumbnail: "/forest-walk.png",
      source: "Pexels",
    },
    { id: 6, type: "image", title: "Sunset Sky", thumbnail: "/sunset-sky.png", source: "Pexels" },
  ]

  const filteredMedia = mockMedia.filter((item) => {
    const matchesSearch = item.title.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCategory = activeCategory === "all" || item.type === activeCategory
    return matchesSearch && matchesCategory
  })

  const handleDragStart = (e: React.DragEvent, mediaItem: any) => {
    const dragData = {
      type: "media",
      mediaId: `online-${mediaItem.id}`,
      mediaType: mediaItem.type,
      title: mediaItem.title,
      duration: mediaItem.type === "video" ? 120 : mediaItem.type === "image" ? 60 : 180,
      isOnline: true,
      thumbnail: mediaItem.thumbnail,
    }
    e.dataTransfer.setData("application/json", JSON.stringify(dragData))
    e.dataTransfer.effectAllowed = "copy"
  }

  return (
    <ScrollArea className="h-full">
      <div className="space-y-4 p-1">
        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search Pexels, Unsplash, Pixabay..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Category Filters */}
        <div className="flex gap-2">
          <Button
            variant={activeCategory === "all" ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveCategory("all")}
            className="gap-2"
          >
            All
          </Button>
          <Button
            variant={activeCategory === "video" ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveCategory("video")}
            className="gap-2"
          >
            <Film className="h-3 w-3" />
            Videos
          </Button>
          <Button
            variant={activeCategory === "image" ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveCategory("image")}
            className="gap-2"
          >
            <ImageIcon className="h-3 w-3" />
            Images
          </Button>
        </div>

        {/* Media Grid */}
        <div className="grid grid-cols-2 gap-3">
          {filteredMedia.map((item) => (
            <Card
              key={item.id}
              className="group cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow"
              draggable
              onDragStart={(e) => handleDragStart(e, item)}
            >
              <div className="relative aspect-[4/3] overflow-hidden rounded-t-lg">
                <img
                  src={item.thumbnail || "/placeholder.svg"}
                  alt={item.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                />

                {/* Overlay with controls */}
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                  <Button size="sm" variant="secondary" className="gap-1">
                    <Play className="h-3 w-3" />
                    Preview
                  </Button>
                  <Button size="sm" variant="secondary" className="gap-1">
                    <Download className="h-3 w-3" />
                    Add
                  </Button>
                </div>

                {/* Type indicator */}
                <div className="absolute top-2 left-2">
                  <Badge variant="secondary" className="text-xs gap-1">
                    {item.type === "video" ? (
                      <>
                        <Film className="h-2 w-2" />
                        {item.duration}
                      </>
                    ) : (
                      <>
                        <ImageIcon className="h-2 w-2" />
                        IMG
                      </>
                    )}
                  </Badge>
                </div>
              </div>

              <CardContent className="p-3">
                <div className="space-y-1">
                  <h4 className="text-sm font-medium truncate">{item.title}</h4>
                  <p className="text-xs text-muted-foreground">by {item.source}</p>
                  <p className="text-xs text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity">
                    Drag to timeline to add
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Load More */}
        <Button variant="outline" className="w-full bg-transparent">
          Load More Results
        </Button>
      </div>
    </ScrollArea>
  )
}

function PropertiesContent() {
  return (
    <ScrollArea className="h-full">
      <div className="space-y-6 p-1">
        {/* Selected Clip Info */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Video className="h-4 w-4" />
              Selected Clip
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">sample-video.mp4</span>
              <Badge variant="secondary">Video</Badge>
            </div>

            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <Label htmlFor="x-pos" className="text-xs">
                  X Position
                </Label>
                <Input id="x-pos" type="number" defaultValue="0" className="h-8" />
              </div>
              <div>
                <Label htmlFor="y-pos" className="text-xs">
                  Y Position
                </Label>
                <Input id="y-pos" type="number" defaultValue="0" className="h-8" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="width" className="text-xs">
                  Width
                </Label>
                <Input id="width" type="number" defaultValue="1920" className="h-8" />
              </div>
              <div>
                <Label htmlFor="height" className="text-xs">
                  Height
                </Label>
                <Input id="height" type="number" defaultValue="1080" className="h-8" />
              </div>
            </div>

            <div>
              <Label className="text-xs">Rotation</Label>
              <div className="flex items-center gap-2 mt-1">
                <Slider defaultValue={[0]} max={360} step={1} className="flex-1" />
                <Button variant="outline" size="sm" className="p-1 h-8 w-8 bg-transparent">
                  <RotateCw className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Transform Controls */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Crop className="h-4 w-4" />
              Transform
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="x-pos" className="text-xs">
                  X Position
                </Label>
                <Input id="x-pos" type="number" defaultValue="0" className="h-8" />
              </div>
              <div>
                <Label htmlFor="y-pos" className="text-xs">
                  Y Position
                </Label>
                <Input id="y-pos" type="number" defaultValue="0" className="h-8" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="width" className="text-xs">
                  Width
                </Label>
                <Input id="width" type="number" defaultValue="1920" className="h-8" />
              </div>
              <div>
                <Label htmlFor="height" className="text-xs">
                  Height
                </Label>
                <Input id="height" type="number" defaultValue="1080" className="h-8" />
              </div>
            </div>

            <div>
              <Label className="text-xs">Rotation</Label>
              <div className="flex items-center gap-2 mt-1">
                <Slider defaultValue={[0]} max={360} step={1} className="flex-1" />
                <Button variant="outline" size="sm" className="p-1 h-8 w-8 bg-transparent">
                  <RotateCw className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Audio Controls */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Volume2 className="h-4 w-4" />
              Audio
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label className="text-xs">Volume</Label>
              <div className="flex items-center gap-2 mt-1">
                <Slider defaultValue={[75]} max={100} step={1} className="flex-1" />
                <span className="text-xs text-muted-foreground w-8">75%</span>
              </div>
            </div>

            <div>
              <Label className="text-xs">Fade In</Label>
              <div className="flex items-center gap-2 mt-1">
                <Slider defaultValue={[0]} max={5} step={0.1} className="flex-1" />
                <span className="text-xs text-muted-foreground w-8">0s</span>
              </div>
            </div>

            <div>
              <Label className="text-xs">Fade Out</Label>
              <div className="flex items-center gap-2 mt-1">
                <Slider defaultValue={[0]} max={5} step={0.1} className="flex-1" />
                <span className="text-xs text-muted-foreground w-8">0s</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Color Correction */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Palette className="h-4 w-4" />
              Color
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label className="text-xs">Brightness</Label>
              <div className="flex items-center gap-2 mt-1">
                <Slider defaultValue={[0]} min={-100} max={100} step={1} className="flex-1" />
                <span className="text-xs text-muted-foreground w-8">0</span>
              </div>
            </div>

            <div>
              <Label className="text-xs">Contrast</Label>
              <div className="flex items-center gap-2 mt-1">
                <Slider defaultValue={[0]} min={-100} max={100} step={1} className="flex-1" />
                <span className="text-xs text-muted-foreground w-8">0</span>
              </div>
            </div>

            <div>
              <Label className="text-xs">Saturation</Label>
              <div className="flex items-center gap-2 mt-1">
                <Slider defaultValue={[0]} min={-100} max={100} step={1} className="flex-1" />
                <span className="text-xs text-muted-foreground w-8">0</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Layer Controls */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Eye className="h-4 w-4" />
              Layer
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label className="text-xs">Opacity</Label>
              <div className="flex items-center gap-2 mt-1">
                <Slider defaultValue={[100]} max={100} step={1} className="flex-1" />
                <span className="text-xs text-muted-foreground w-10">100%</span>
              </div>
            </div>

            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="flex-1 gap-2 bg-transparent">
                <Eye className="h-3 w-3" />
                Visible
              </Button>
              <Button variant="outline" size="sm" className="flex-1 bg-transparent">
                Lock
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  )
}

export function PropertiesPanel() {
  return (
    <div className="h-full flex flex-col bg-card">
      <Tabs defaultValue="properties" className="w-full h-full flex flex-col">
        <TabsList className="grid w-full grid-cols-3 h-12 rounded-none bg-transparent border-0 border-b border-border flex-shrink-0">
          <TabsTrigger
            value="properties"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent text-xs"
          >
            Properties
          </TabsTrigger>
          <TabsTrigger
            value="media-pool"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent text-xs"
          >
            Media Pool
          </TabsTrigger>
          <TabsTrigger
            value="media"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent text-xs"
          >
            Media Library
          </TabsTrigger>
        </TabsList>

        <div className="flex-1 overflow-hidden">
          <TabsContent value="properties" className="h-full mt-0 p-4">
            <PropertiesContent />
          </TabsContent>

          <TabsContent value="media-pool" className="h-full mt-0 p-4">
            <MediaPool />
          </TabsContent>

          <TabsContent value="media" className="h-full mt-0 p-4">
            <MediaLibrary />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  )
}
