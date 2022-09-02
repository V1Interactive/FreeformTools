/*
 * Freeform Rigging and Animation Tools
 * Copyright (C) 2020  Micah Zahm
 *
 * Freeform Rigging and Animation Tools is free software: you can redistribute it 
 * and/or modify it under the terms of the GNU General Public License as published 
 * by the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Freeform Rigging and Animation Tools is distributed in the hope that it will 
 * be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Freeform Rigging and Animation Tools.  
 * If not, see <https://www.gnu.org/licenses/>.
 */

namespace Freeform.Rigging
{
    using Freeform.Core.ConfigSettings;
    using Freeform.Core.UI;
    using HelixResources.Style;
    using System;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.ComponentModel;
    using System.IO;
    using System.Linq;
    using System.Windows;
    using System.Windows.Data;
    using System.Windows.Forms;
    using System.Windows.Input;
    using System.Windows.Media;

    class RiggerVM : ViewModelBase
    {
        #region EventHandlers
        public event EventHandler UpdateEventHandler;
        public event EventHandler ExportAllHandler;
        public event EventHandler ExporterUiHandler;
        public event EventHandler LoadSettingsHandler;
        public event EventHandler GetStartingDirectoryHandler;
        public event EventHandler SaveSettingsHandler;
        public event EventHandler SaveUE4SettingsHandler;
        public event EventHandler OpenRegionEditorHandler;
        public event EventHandler RigBuilderHandler;
        public event EventHandler ColorSetsHandler;
        public event EventHandler SaveRiggingHandler;
        public event EventHandler LoadRiggingHandler;
        public event EventHandler RemoveAnimationHandler;
        public event EventHandler SelectAllHandler;
        public event EventHandler UpdateCharacterHandler;
        public event EventHandler HIKCharacterizeHandler;
        public event EventHandler AddNewJointsHandler;
        public event EventHandler UpdateCharacterNamespaceHandler;
        public event EventHandler UpdateCharacterNameHandler;
        public event EventHandler SetColorSetHandler;
        public event EventHandler SetBindCharacterHandler;
        public event EventHandler FreezeCharacterHandler;
        public event EventHandler SetRigPathHandler;
        public event EventHandler DeleteCharacterHandler;
        public event EventHandler QuickFKCharacterHandler;
        public event EventHandler MirrorAnimationHandler;
        public event EventHandler ZeroRigHandler;
        public event EventHandler ZeroCharacterHandler;
        public event EventHandler SwapCharacterHandler;
        public event EventHandler TransferJointsHandler;
        public event EventHandler TransferHIKHandler;
        public event EventHandler ImportUE4AnimationHandler;
        public event EventHandler SaveBakeRangeHandler;
        public event EventHandler SaveSettingHandler;
        public event EventHandler OpenCharacterImporterHandler;
        public event EventHandler SetActiveCharacterHandler;
        public event EventHandler SaveQuickSelectHandler;
        public event EventHandler CreateQuickSelectHandler;
        public event EventHandler RunQuickSelectHandler;
        public event EventHandler LoadCharacterHandler;
        #endregion

        #region RelayCommands
        public RelayCommand UpdateCommand { get; set; }
        public RelayCommand ExportCommand { get; set; }
        public RelayCommand ExporterUICommand { get; set; }
        public RelayCommand LoadSettingsCommand { get; set; }
        public RelayCommand SaveSettingsCommand { get; set; }
        public RelayCommand SaveUE4SettingsCommand { get; set; }
        public RelayCommand RigRegionCommand { get; set; }
        public RelayCommand OpenRegionEditorCommand { get; set; }
        public RelayCommand SetCharacterCommand { get; set; }
        public RelayCommand SetTargetCharacterCommand { get; set; }
        public RelayCommand AddNewJointsCommand { get; set; }
        public RelayCommand HIKCharacterizeCommand { get; set; }
        public RelayCommand UpdateCharacterNamespaceCommand { get; set; }
        public RelayCommand UpdateCharacterNameCommand { get; set; }
        public RelayCommand SetBindCharacterCommand { get; set; }
        public RelayCommand FreezeCharacterCommand { get; set; }
        public RelayCommand SetRigPathCommand { get; set; }
        public RelayCommand SetColorSetCommand { get; set; }
        public RelayCommand DeleteCharacterCommand { get; set; }
        public RelayCommand QuickFKCharacterCommand { get; set; }
        public RelayCommand RigBuilderCommand { get; set; }
        public RelayCommand ColorSetsCommand { get; set; }
        public RelayCommand SaveRiggingCommand { get; set; }
        public RelayCommand LoadRiggingCommand { get; set; }
        //public RelayCommand TransferAllAnimCommand { get; set; }
        public RelayCommand TransferAllJointsCommand { get; set; }
        public RelayCommand TransferAllHIKCommand { get; set; }
        public RelayCommand ImportUE4AnimationCommand { get; set; }
        public RelayCommand RemoveAnimationCommand { get; set; }
        public RelayCommand SelectAllAnimatedCommand { get; set; }
        public RelayCommand SelectAllCommand { get; set; }
        public RelayCommand MirrorAnimationCommand { get; set; }
        public RelayCommand ZeroRigCommand { get; set; }
        public RelayCommand ZeroCharacterCommand { get; set; }
        public RelayCommand SwapCharacterCommand { get; set; }
        public RelayCommand UpdateCharacterCommand { get; set; }
        public RelayCommand SelectGroupCommand { get; set; }
        public RelayCommand BakeRangeCommand { get; set; }
        public RelayCommand OpenCharacterImporterCommand { get; set; }
        public RelayCommand LoadCharacterCommand { get; set; }
        public RelayCommand UnloadCharacterCommand { get; set; }
        public RelayCommand AddQuickSearchCommand { get; set; }
        public RelayCommand RemoveQuickSearchCommand { get; set; }
        

        public RelayCommand HelpCommand { get; set; }
        #endregion


        public ObservableCollection<RigBarCategory> _rigCategoryList;
        public ObservableCollection<RigBarCategory> RigCategoryList
        {
            get { return _rigCategoryList; }
            set
            {
                if (_rigCategoryList != value)
                {
                    _rigCategoryList = value;
                    RaisePropertyChanged("RigCategoryList");
                }
            }
        }

        public ObservableCollection<SelectBarButton> _selectButtonList;
        public ObservableCollection<SelectBarButton> SelectButtonList
        {
            get { return _selectButtonList; }
            set
            {
                if (_selectButtonList != value)
                {
                    _selectButtonList = value;
                    RaisePropertyChanged("SelectButtonList");
                }
            }
        }
        public CollectionViewSource SelectButtonViewSource { get; set; }


        public ObservableCollection<string> _settingsPresetList;
        public ObservableCollection<string> SettingsPresetList
        {
            get { return _settingsPresetList; }
            set
            {
                if (_settingsPresetList != value)
                {
                    _settingsPresetList = value;
                    RaisePropertyChanged("SettingsPresetList");
                }
            }
        }

        string _selectedPreset;
        public string SelectedPreset
        {
            get { return _selectedPreset; }
            set
            {
                if (_selectedPreset != value)
                {
                    _selectedPreset = value;
                    RaisePropertyChanged("SelectedPreset");
                }
            }
        }

        public ObservableCollection<V1MenuItem> _settingsMenuItems;
        public ObservableCollection<V1MenuItem> SettingsMenuItems
        {
            get { return _settingsMenuItems; }
            set
            {
                if (_settingsMenuItems != value)
                {
                    _settingsMenuItems = value;
                    RaisePropertyChanged("SettingsMenuItems");
                }
            }
        }

        public ObservableCollection<V1MenuItem> _riggingMenuItems;
        public ObservableCollection<V1MenuItem> RiggingMenuItems
        {
            get { return _riggingMenuItems; }
            set
            {
                if (_riggingMenuItems != value)
                {
                    _riggingMenuItems = value;
                    RaisePropertyChanged("RiggingMenuItems");
                }
            }
        }

        public ObservableCollection<string> _rigTypes;
        public ObservableCollection<string> RigTypes
        {
            get { return _rigTypes; }
            set
            {
                if (_rigTypes != value)
                {
                    _rigTypes = value;
                    RaisePropertyChanged("RigTypes");
                }
            }
        }

        string _selectedRigType;
        public string SelectedRigType
        {
            get { return _selectedRigType; }
            set
            {
                if (_selectedRigType != value)
                {
                    _selectedRigType = value;
                    RaisePropertyChanged("SelectedRigType");
                }
            }
        }

        ObservableCollection<PropFile> _propList;
        public ObservableCollection<PropFile> PropList
        {
            get { return _propList; }
            set
            {
                if (_propList != value)
                {
                    _propList = value;
                    RaisePropertyChanged("PropList");
                }
            }
        }

        public ObservableCollection<Character> _characterList;
        public ObservableCollection<Character> CharacterList
        {
            get { return _characterList; }
            set
            {
                if (_characterList != value)
                {
                    _characterList = value;
                    RaisePropertyChanged("CharacterList");
                }
            }
        }

        Character _activeCharacter;
        public Character ActiveCharacter
        {
            get { return _activeCharacter; }
            set
            {
                if (_activeCharacter != value)
                {
                    _activeCharacter = value;
                    if (_activeCharacter != null)
                    {
                        _activeCharacter.ComponentSearchFilter = FilterComponentText;
                        _activeCharacter.RegionSearchFilter = FilterRegionText;

                        SettingsMenuItems.Clear();
                        RiggingMenuItems.Clear();
                        SetActiveCharacterHandler?.Invoke(this, null);
                    }
                    
                    RaisePropertyChanged("ActiveCharacter");
                }
            }
        }

        Character _targetCharacter;
        public Character TargetCharacter
        {
            get { return _targetCharacter; }
            set
            {
                if (_targetCharacter != value)
                {
                    _targetCharacter = value;
                    RaisePropertyChanged("TargetCharacter");
                }
            }
        }

        bool _isWorldSpace;
        public bool IsWorldSpace
        {
            get { return _isWorldSpace; }
            set
            {
                if (_isWorldSpace != value)
                {
                    _isWorldSpace = value;
                    RaisePropertyChanged("IsWorldSpace");
                }
            }
        }

        bool _incrementVersion;
        public bool IncrementVersion
        {
            get { return _incrementVersion; }
            set
            {
                if (_incrementVersion != value)
                {
                    _incrementVersion = value;
                    RaisePropertyChanged("IncrementVersion");
                }
            }
        }

    bool _removeExisting;
        public bool RemoveExisting
        {
            get { return _removeExisting; }
            set
            {
                if (_removeExisting != value)
                {
                    _removeExisting = value;
                    RaisePropertyChanged("RemoveExisting");
                    SaveSettingHandler?.Invoke(this, new SaveBoolEventArgs() { name = "remove_existing", value = _removeExisting, category = "CharacterSettings" });
                }
            }
        }

        bool _worldOrientIK;
        public bool WorldOrientIK
        {
            get { return _worldOrientIK; }
            set
            {
                if (_worldOrientIK != value)
                {
                    _worldOrientIK = value;
                    RaisePropertyChanged("WorldOrientIK");
                    SaveSettingHandler?.Invoke(this, new SaveBoolEventArgs() { name = "world_orient_ik", value = _worldOrientIK, category = "CharacterSettings" });
                }
            }
        }

        bool _noBakeOverdrivers;
        public bool NoBakeOverdrivers
        {
            get { return _noBakeOverdrivers; }
            set
            {
                if (_noBakeOverdrivers != value)
                {
                    _noBakeOverdrivers = value;
                    RaisePropertyChanged("NoBakeOverdrivers");
                    SaveSettingHandler?.Invoke(this, new SaveBoolEventArgs() { name = "no_bake_overdrivers", value = _noBakeOverdrivers, category = "CharacterSettings" });
                }
            }
        }

        bool _bakeDrivers;
        public bool BakeDrivers
        {
            get { return _bakeDrivers; }
            set
            {
                if (_bakeDrivers != value)
                {
                    _bakeDrivers = value;
                    RaisePropertyChanged("BakeDrivers");
                    SaveSettingHandler?.Invoke(this, new SaveBoolEventArgs() { name = "bake_drivers", value = _bakeDrivers, category = "CharacterSettings" });
                }
            }
        }

        bool _uiManualUpdate;
        public bool UiManualUpdate
        {
            get { return _uiManualUpdate; }
            set
            {
                _uiManualUpdate = value;
                RaisePropertyChanged("UiManualUpdate");
                SaveSettingHandler?.Invoke(this, new SaveBoolEventArgs() { name = "ui_manual_update", value = _uiManualUpdate, category = "OptimizationSettings" });
            }
        }

        bool _bakeOverdrivers;
        public bool BakeOverdrivers
        {
            get { return _bakeOverdrivers; }
            set
            {
                if (_bakeOverdrivers != value)
                {
                    _bakeOverdrivers = value;
                    RaisePropertyChanged("BakeOverdrivers");
                    SaveSettingHandler?.Invoke(this, new SaveBoolEventArgs() { name = "bake_overdriver", value = _bakeOverdrivers, category = "OverdriverSettings" });
                }
            }
        }

        bool _bakeComponent;
        public bool BakeComponent
        {
            get { return _bakeComponent; }
            set
            {
                if (_bakeComponent != value)
                {
                    _bakeComponent = value;
                    RaisePropertyChanged("BakeComponent");

                    if (value)
                    {
                        RevertAnimation = !value;
                        RaisePropertyChanged("RevertAnimation");
                    }

                    SaveSettingHandler?.Invoke(this, new SaveBoolEventArgs() { name = "bake_component", value = _bakeComponent, category = "CharacterSettings" });

                    if (value)
                    {
                        GetRigButtonFromCategory(GetRigCategoryList("Bake/Remove Components"), "Remove Component").StatusImagePath = "../../Resources/bake_remove_rig.ico";
                        GetRigButtonFromCategory(GetRigCategoryList("Miscellaneous"), "Re-Parent Component").StatusImagePath = "../../Resources/bake_remove_rig.ico";
                        GetRigButtonFromCategory(GetRigCategoryList("Space Switching"), "Dynamics - AIM").StatusImagePath = "../../Resources/bake_remove_rig.ico";
                    }
                    else if (!RevertAnimation)
                    {
                        // If RevertAnimation is true it will set the StatusImagePath, so don't clear it
                        GetRigButtonFromCategory(GetRigCategoryList("Bake/Remove Components"), "Remove Component").StatusImagePath = "";
                    }

                    if (!value)
                    {
                        GetRigButtonFromCategory(GetRigCategoryList("Miscellaneous"), "Re-Parent Component").StatusImagePath = "";
                        GetRigButtonFromCategory(GetRigCategoryList("Space Switching"), "Dynamics - AIM").StatusImagePath = "";
                    }
                }
            }
        }

        bool _revertAnimation;
        public bool RevertAnimation
        {
            get { return _revertAnimation; }
            set
            {
                if (_revertAnimation != value)
                {
                    _revertAnimation = value;
                    RaisePropertyChanged("RevertAnimation");

                    if (value)
                    {
                        BakeComponent = !value;
                        RaisePropertyChanged("BakeComponent");
                    }

                    SaveSettingHandler?.Invoke(this, new SaveBoolEventArgs() { name = "revert_animation", value = _revertAnimation, category = "CharacterSettings" });

                    if (value)
                    {
                        GetRigButtonFromCategory(GetRigCategoryList("Bake/Remove Components"), "Remove Component").StatusImagePath = "../../Resources/remove_revert.png";
                    }
                    else if (!BakeComponent)
                    {
                        GetRigButtonFromCategory(GetRigCategoryList("Bake/Remove Components"), "Remove Component").StatusImagePath = "";
                    }
                }
            }
        }

        bool _forceRemove;
        public bool ForceRemove
        {
            get { return _forceRemove; }
            set
            {
                if (_forceRemove != value)
                {
                    _forceRemove = value;
                    RaisePropertyChanged("ForceRemove");

                    SaveSettingHandler?.Invoke(this, new SaveBoolEventArgs() { name = "force_remove", value = _forceRemove, category = "CharacterSettings" });

                    if (value)
                        GetRigCategoryList("Bake/Remove Components").RigButtonList.First().ImagePath = "../../Resources/trashcan.png";
                    else
                        GetRigCategoryList("Bake/Remove Components").RigButtonList.First().ImagePath = "../../Resources/remove.ico";
                }
            }
        }

        string _sideEntry;
        public string SideEntry
        {
            get { return _sideEntry; }
            set
            {
                if (_sideEntry != value)
                {
                    _sideEntry = value;
                    RaisePropertyChanged("SideEntry");
                }
            }
        }

        string _regionEntry;
        public string RegionEntry
        {
            get { return _regionEntry; }
            set
            {
                if (_regionEntry != value)
                {
                    _regionEntry = value;
                    RaisePropertyChanged("RegionEntry");
                }
            }
        }

        string _rootEntry;
        public string RootEntry
        {
            get { return _rootEntry; }
            set
            {
                if (_rootEntry != value)
                {
                    _rootEntry = value;
                    RaisePropertyChanged("RootEntry");
                }
            }
        }

        string _endEntry;
        public string EndEntry
        {
            get { return _endEntry; }
            set
            {
                if (_endEntry != value)
                {
                    _endEntry = value;
                    RaisePropertyChanged("EndEntry");
                }
            }
        }

    string _quickSelectText;
        public string QuickSelectText
        {
            get { return _quickSelectText; }
            set
            {
                _quickSelectText = value;
                RaisePropertyChanged("QuickSelectText");
            }
        }

        string _filterComponentText;
        public string FilterComponentText
        {
            get { return _filterComponentText; }
            set
            {
                _filterComponentText = value;
                if(ActiveCharacter != null)
                {
                    ActiveCharacter.ComponentSearchFilter = value;
                }
                RaisePropertyChanged("FilterComponentText");
            }
        }

        string _filterRegionText;
        public string FilterRegionText
        {
            get { return _filterRegionText; }
            set
            {
                _filterRegionText = value;
                if (ActiveCharacter != null)
                {
                    ActiveCharacter.RegionSearchFilter = value;
                }
                RaisePropertyChanged("FilterRegionText");
            }
        }

        int _characterIndex;
        public int CharacterIndex
        {
            get { return _characterIndex; }
            set
            {
                if (_characterIndex != value)
                {
                    _characterIndex = value;
                    if (value != -1)
                    {
                        ActiveCharacter = CharacterList[value];
                    }
                    RaisePropertyChanged("CharacterIndex");
                }
            }
        }

        int _startFrame;
        public int StartFrame
        {
            get { return _startFrame; }
            set
            {
                if(_startFrame != value)
                {
                    _startFrame = value;
                    RaisePropertyChanged("StartFrame");
                    SaveSettingHandler?.Invoke(this, new SaveIntEventArgs() { name = "start_frame", value = _startFrame, category = "BakeSettings" });
                }
            }
        }

        int _endframe;
        public int EndFrame
        {
            get { return _endframe; }
            set
            {
                if (_endframe != value)
                {
                    _endframe = value;
                    RaisePropertyChanged("EndFrame");
                    SaveSettingHandler?.Invoke(this, new SaveIntEventArgs() { name = "end_frame", value = _endframe, category = "BakeSettings" });
                }
            }
        }

        int _sampleBy;
        public int SampleBy
        {
            get { return _sampleBy; }
            set
            {
                if (_sampleBy != value)
                {
                    _sampleBy = value;
                    RaisePropertyChanged("SampleBy");
                    SaveSettingHandler?.Invoke(this, new SaveIntEventArgs() { name = "sample_by", value = _sampleBy, category = "BakeSettings" });
                }
            }
        }

        public void AddRigType(string cls_name)
        {
            RigTypes.Add(cls_name);
        }

        public void UpdateRiggerInPlace()
        {
            UpdateInPlaceCall(null);
        }

        public void UpdateInPlaceCall(object sender)
        {
            var currentIndex = CharacterIndex != -1 ? CharacterIndex : 0;
            UpdateRiggerUI();

            if (ActiveCharacter != null)
            {
                ActiveCharacter.IsSelected = false;
                ActiveCharacter = CharacterList[currentIndex];
                CharacterIndex = currentIndex;
                ActiveCharacter.IsSelected = true;
            }
        }

        public void UpdateRiggerUI()
        {
            SettingsMenuItems.Clear();
            RiggingMenuItems.Clear();
            ActiveCharacter = null;
            TargetCharacter = null;

            UpdateEventHandler?.Invoke(this, null);

            SetDefaultActiveCharacter();
        }

        public void SetDefaultActiveCharacter()
        {
            if (CharacterList.FirstOrDefault() != null)
            {
                // Set both incase Index is already 0.
                ActiveCharacter = CharacterList[0];
                CharacterIndex = 0;
                CharacterList[0].IsSelected = true;

                ActiveCharacter.ComponentSearchFilter = FilterComponentText;
                ActiveCharacter.RegionSearchFilter = FilterRegionText;
            }
            else
            {
                ActiveCharacter = null;
                CharacterIndex = -1;
            }
        }

        public bool[] BakeRange { get; set; } = new bool[] { true, false, false, false };
        public int SelectedBakeRange
        {
            get { return Array.IndexOf(BakeRange, true); }
        }

        bool _frameRangeEnabled;
        public bool FrameRangeEnabled
        {
            get { return _frameRangeEnabled; }
            set
            {
                if (_frameRangeEnabled != value)
                {
                    _frameRangeEnabled = value;
                    RaisePropertyChanged("FrameRangeEnabled");
                }
            }
        }

        bool _smartBake;
        public bool SmartBake
        {
            get { return _smartBake; }
            set
            {
                if(_smartBake != value)
                {
                    _smartBake = value;
                    RaisePropertyChanged("SmartBake");
                    SaveSettingHandler?.Invoke(this, new SaveBoolEventArgs() { name = "smart_bake", value = _smartBake, category = "BakeSettings" });
                }
            }
        }


        public RiggerVM()
        {
            CharacterIndex = -1;

            UpdateCommand = new RelayCommand(UpdateInPlaceCall);
            ExportCommand = new RelayCommand(ExportEventCall);
            ExporterUICommand = new RelayCommand(ExporterUICall);
            LoadSettingsCommand = new RelayCommand(LoadSettingsCall);
            SaveSettingsCommand = new RelayCommand(SaveSettingsCall);
            SaveUE4SettingsCommand = new RelayCommand(SaveUE4SettingsCall);
            RigRegionCommand = new RelayCommand(RigRegionEventCall);
            OpenRegionEditorCommand = new RelayCommand(OpenRegionEditorEventCall);
            SetCharacterCommand = new RelayCommand(SetActiveCharacterCall);
            SetTargetCharacterCommand = new RelayCommand(SetTargetCharacterCall);
            AddNewJointsCommand = new RelayCommand(AddNewJointsCall);
            HIKCharacterizeCommand = new RelayCommand(HIKCharacterizeCall);
            UpdateCharacterNamespaceCommand = new RelayCommand(UpdateCharacterNamespaceCall);
            UpdateCharacterNameCommand = new RelayCommand(UpdateCharacterNameCall);
            SetBindCharacterCommand = new RelayCommand(SetBindCharacterCall);
            FreezeCharacterCommand = new RelayCommand(FreezeCharacterCall);
            SetRigPathCommand = new RelayCommand(SetRigPathCall);
            SetColorSetCommand = new RelayCommand(SetColorSetCall);
            DeleteCharacterCommand = new RelayCommand(DeleteCharacterCall);
            QuickFKCharacterCommand = new RelayCommand(QuickFKCharacterCall);
            RemoveAnimationCommand = new RelayCommand(RemoveAnimationCall);
            SelectAllAnimatedCommand = new RelayCommand(SelectAllAnimatedCall);
            SelectAllCommand = new RelayCommand(SelectAllCall);
            ZeroRigCommand = new RelayCommand(ZeroRigCall);
            ZeroCharacterCommand = new RelayCommand(ZeroCharacterCall);
            SwapCharacterCommand = new RelayCommand(SwapCharacterCall);
            RigBuilderCommand = new RelayCommand(RigBuilderCall);
            ColorSetsCommand = new RelayCommand(ColorSetsCall);
            SaveRiggingCommand = new RelayCommand(SaveRiggingCall);
            LoadRiggingCommand = new RelayCommand(LoadRiggingCall);
            SelectGroupCommand = new RelayCommand(SelectGroupCall);
            BakeRangeCommand = new RelayCommand(BakeRangeCall);

            //TransferAllAnimCommand = new RelayCommand(TransferAllAnimCall);
            TransferAllJointsCommand = new RelayCommand(TransferAllJointsCall);
            TransferAllHIKCommand = new RelayCommand(TransferAllHIKCall);
            ImportUE4AnimationCommand = new RelayCommand(ImportUE4AnimationCall);

            UpdateCharacterCommand = new RelayCommand(UpdateCharacterEventCall);

            OpenCharacterImporterCommand = new RelayCommand(OpenCharacterImporterCall);
            LoadCharacterCommand = new RelayCommand(LoadCharacterCall);
            UnloadCharacterCommand = new RelayCommand(UnloadCharacterCall);

            MirrorAnimationCommand = new RelayCommand(MirrorAnimationCall);

            AddQuickSearchCommand = new RelayCommand(AddQuickSearchCall);
            RemoveQuickSearchCommand = new RelayCommand(RemoveQuickSearchCall);

            HelpCommand = new RelayCommand(HelpCall);

            FilterComponentText = "";
            FilterRegionText = "";
            TargetCharacter = null;
            IsWorldSpace = false;
            RootEntry = "Pick Root";
            EndEntry = "Pick End";

            RigCategoryList = new ObservableCollection<RigBarCategory>();
            SelectButtonList = new ObservableCollection<SelectBarButton>();
            SelectButtonViewSource = new CollectionViewSource
            {
                Source = SelectButtonList
            };
            SelectButtonViewSource.SortDescriptions.Add(new SortDescription("Name", ListSortDirection.Ascending));

            CharacterList = new ObservableCollection<Character>();
            SettingsPresetList = new ObservableCollection<string>();

            SettingsMenuItems = new ObservableCollection<V1MenuItem>();
            RiggingMenuItems = new ObservableCollection<V1MenuItem>();

            RigTypes = new ObservableCollection<string>();

            PropList = new ObservableCollection<PropFile>();
        }


        public void WindowsDeactivatedCall()
        {
            
        }


        #region Event Calls
        public void HelpCall(object sender)
        {
            var hit = VisualTreeHelper.HitTest((UIElement)sender, Mouse.GetPosition((UIElement)sender));
            var item = hit?.VisualHit;
            
            while (item != null)
            {
                // Exit if we find a valid Tag or a Button that we want to use the DataContext of
                if ((item is FrameworkElement itemElement && itemElement.Tag != null) ||
                    (item is System.Windows.Controls.Button buttonObject && (buttonObject.DataContext is ComponentSelectButton || buttonObject.DataContext is RigBarButton)))
                    break;
                item = VisualTreeHelper.GetParent(item);
            }

            string helpPage = "https://sites.google.com/view/v1freeformtools/home/rigging";
            string pageName = "";

            if (item == null)
            {
                // Do Nothing with the page name
            }
            else if (item is System.Windows.Controls.Button buttonObject)
            {
                if (buttonObject.DataContext is ComponentSelectButton selectButtonContext)
                    pageName = "/" + selectButtonContext.Name;
                else if (buttonObject.DataContext is RigBarButton buttonContext)
                    pageName = string.Format("/toolbar-buttons/{0}", buttonContext.Name);
                else
                    pageName = "/" + buttonObject.Tag;
            }
            else if (item is System.Windows.Controls.ComboBox comboBoxObject)
            {
                pageName = string.Format("/{0}__{1}", comboBoxObject.Tag, comboBoxObject.Text);
            }
            else
            {
                FrameworkElement itemElement = (FrameworkElement)item;
                pageName = "/" + itemElement.Tag;
            }


            // Fixup UI valid names to webpage valid names
            pageName = pageName == "/" ? "" : pageName;
            pageName = pageName.Replace(" - ", "-");
            pageName = pageName.Replace("__", "/").Replace("_", "-").Replace(" ", "-");
            helpPage += pageName.ToLower();
            System.Diagnostics.Process.Start(helpPage);
        }

        public void OpenCharacterImporterCall(object sender)
        {
            OpenCharacterImporterHandler?.Invoke(this, null);
        }

        public void LoadCharacterCall(object sender)
        {
            CharacterEventArgs eventArgs = new CharacterEventArgs();
            LoadCharacterHandler?.Invoke(this, eventArgs);
            if(eventArgs.character != null)
                SetActiveCharacterCall(eventArgs.character);
        }

        public void UnloadCharacterCall(object sender)
        {
            UnloadCharacter(ActiveCharacter, true);
        }

        public void UnloadCharacter(Character character, bool updateCharacter)
        {
            CharacterList.Remove(character);
            if (updateCharacter)
            {
                SetDefaultActiveCharacter();
            }
        }

        public void BakeRangeCall(object sender)
        {
            FrameRangeEnabled = BakeRange[2];
            SaveBakeRangeHandler?.Invoke(this, new BakeRangeEventArgs() { BakeRange = BakeRange });
        }

        public RigBarCategory GetRigCategoryList(string categoryName)
        {
            RigBarCategory returnCategory = null;
            foreach (RigBarCategory category in RigCategoryList)
            {
                if (category.Name == categoryName)
                    returnCategory = category;
            }
            return returnCategory;
        }

        public RigBarButton GetRigButtonFromCategory(RigBarCategory category, string buttonName)
        {
            RigBarButton returnButton = null;
            foreach (RigBarButton button in category.RigButtonList)
            {
                if (button.Name == buttonName)
                    returnButton = button;
            }
            return returnButton;
        }

        public void AddQuickSearchCall(object sender)
        {
            if(QuickSelectText != string.Empty || QuickSelectText != null)
            {
                SelectBarButton button = CreateQuickSearchButton(QuickSelectText);

                CreateButtonEventArgs createArgs = new CreateButtonEventArgs
                {
                    SelectButton = button
                };
                CreateQuickSelectHandler?.Invoke(this, createArgs);

                SelectButtonEventArgs eventArgs = new SelectButtonEventArgs
                {
                    SelectButtonList = SelectButtonList.ToList()
                };
                SaveQuickSelectHandler?.Invoke(this, eventArgs);
            }
        }

        public SelectBarButton CreateQuickSearchButton(string searchString)
        {
            SelectBarButton newButton = new SelectBarButton
            {
                Name = searchString
            };
            newButton.CommandHandler += QuickSelectButtonCall;

            SelectButtonList.Add(newButton);
            return newButton;
        }

        private void QuickSelectButtonCall(object sender, EventArgs e)
        {
            SelectBarButton button = (SelectBarButton)sender;

            CreateButtonEventArgs eventArgs = new CreateButtonEventArgs
            {
                SelectButton = button
            };
            RunQuickSelectHandler?.Invoke(this, eventArgs);
        }

        public void RemoveQuickSearchCall(object sender)
        {
            SelectBarButton removeButton = (SelectBarButton)sender;
            SelectButtonList.Remove(removeButton);

            SelectButtonEventArgs eventArgs = new SelectButtonEventArgs
            {
                SelectButtonList = SelectButtonList.ToList()
            };
            SaveQuickSelectHandler?.Invoke(this, eventArgs);
        }

        //public void TransferAllAnimCall(object sender)
        //{
        //    foreach(Component comp in ActiveCharacter.Components)
        //    {
        //        comp.TransferAnimEventCall(sender);
        //    }
        //}

        public void TransferAllJointsCall(object sender)
        {
            if(TargetCharacter != null)
            {
                Character character = (Character)sender;
                TransferEventArgs eventArgs = new TransferEventArgs()
                {
                    sourceCharacter = TargetCharacter,
                    destinationCharacter = character
                };
                TransferJointsHandler?.Invoke(this, eventArgs);
            }
        }

        public void TransferAllHIKCall(object sender)
        {
            if (TargetCharacter != null)
            {
                Character character = (Character)sender;
                TransferEventArgs eventArgs = new TransferEventArgs()
                {
                    sourceCharacter = TargetCharacter,
                    destinationCharacter = character
                };
                TransferHIKHandler?.Invoke(this, eventArgs);
            }
        }

        public void ImportUE4AnimationCall(object sender)
        {
            Character character = (Character)sender;

            using (OpenFileDialog filesDialog = new OpenFileDialog())
            {
                filesDialog.Title = "Load UE4 Exported Animation";
                filesDialog.Filter = "JSON file (*.fbx)|*.fbx";
                filesDialog.RestoreDirectory = true;

                DialogResult fileResult = filesDialog.ShowDialog();
                if (fileResult == DialogResult.OK)
                {
                    CharacterFileEventArgs eventArgs = new CharacterFileEventArgs()
                    {
                        character = character,
                        filePath = filesDialog.FileName
                    };
                    ImportUE4AnimationHandler?.Invoke(this, eventArgs);
                }
            }
        }

        public void SelectGroupCall(object sender)
        {
            string senderName = (string)sender;
            if (ActiveCharacter != null)
            {
                ActiveCharacter.SelectGroupCall(ActiveCharacter.GetComponentGroup(senderName), false);
            }   
        }

        public void UpdateCharacterEventCall(object sender)
        {
            Character character = (Character)sender;
            UpdateCharacterEventArgs eventArgs = new UpdateCharacterEventArgs()
            {
                character = character
            };
            UpdateCharacterHandler?.Invoke(this, eventArgs);

            character.OutOfDate = !eventArgs.updated;
        }

        public void MirrorAnimationCall(object sender)
        {
            Character character = (Character)sender;
            CharacterEventArgs eventArgs = new CharacterEventArgs()
            {
                character = character
            };

            ZeroRigCall(character);
            SetActiveCharacterCall(character);
            MirrorAnimationHandler?.Invoke(this, eventArgs);
        }

        public void ZeroRigCall(object sender)
        {
            Character character = (Character)sender;
            CharacterEventArgs eventArgs = new CharacterEventArgs()
            {
                character = character
            };
            ZeroRigHandler?.Invoke(this, eventArgs);
        }

        public void ZeroCharacterCall(object sender)
        {
            Character character = (Character)sender;
            CharacterEventArgs eventArgs = new CharacterEventArgs()
            {
                character = character
            };
            ZeroCharacterHandler?.Invoke(this, eventArgs);
        }

        public void SwapCharacterCall(object sender)
        {
            Character character = (Character)sender;
            CharacterEventArgs eventArgs = new CharacterEventArgs()
            {
                character = character
            };
            SwapCharacterHandler?.Invoke(this, eventArgs);
        }

        public void RemoveAnimationCall(object sender)
        {
            CharacterEventArgs eventArgs = new CharacterEventArgs()
            {
                character = (Character)sender
            };
            RemoveAnimationHandler?.Invoke(this, eventArgs);
        }

        public void SelectAllAnimatedCall(object sender)
        {
            SelectionEventArgs eventArgs = new SelectionEventArgs()
            {
                character = (Character)sender,
                animated = true
            };
            SelectAllHandler?.Invoke(this, eventArgs);
        }

        public void SelectAllCall(object sender)
        {
            SelectionEventArgs eventArgs = new SelectionEventArgs()
            {
                character = (Character)sender,
                animated = false
            };
            SelectAllHandler?.Invoke(this, eventArgs);
        }

        public void SetActiveCharacterCall(object sender)
        {
            Character new_character = (Character)sender;
            if (ActiveCharacter != null)
                ActiveCharacter.IsSelected = false;
            new_character.IsSelected = true;

            int index = CharacterList.IndexOf(new_character);
            if(CharacterIndex == index)
            {
                // Roundabout way to call SelectAllGroups encapsulated in a Maya undo block
                // SelectAllGroupsCall() -> Character SelectAllGroupsHandler() -> python select_all_groups() -> Character SelectAllGroups()
                new_character.SelectAllGroupsCall();
            }
            else
            {
                SettingsMenuItems.Clear();
                RiggingMenuItems.Clear();

                CharacterIndex = index;
            }
        }

        public void SetTargetCharacterCall(object sender)
        {
            TargetCharacter = (Character)sender;
        }

        public void AddNewJointsCall(object sender)
        {
            CharacterEventArgs eventArgs = new CharacterEventArgs()
            {
                character = (Character)sender
            };
            AddNewJointsHandler?.Invoke(this, eventArgs);
        }

        public void HIKCharacterizeCall(object sender)
        {
            CharacterEventArgs eventArgs = new CharacterEventArgs()
            {
              character = (Character)sender
            };
            HIKCharacterizeHandler?.Invoke(this, eventArgs);
        }

        public void UpdateCharacterNamespaceCall(object sender)
        {
            CharacterEventArgs eventArgs = new CharacterEventArgs()
            {
                character = (Character)sender
            };
            UpdateCharacterNamespaceHandler?.Invoke(this, eventArgs);
        }

        public void UpdateCharacterNameCall(object sender)
        {
            CharacterEventArgs eventArgs = new CharacterEventArgs()
            {
                character = (Character)sender
            };
            UpdateCharacterNameHandler?.Invoke(this, eventArgs);
        }

        public void SetColorSetCall(object sender)
        {
            CharacterEventArgs eventArgs = new CharacterEventArgs()
            {
                character = (Character)sender
            };
            SetColorSetHandler?.Invoke(this, eventArgs);
        }

        public void SetBindCharacterCall(object sender)
        {
            CharacterEventArgs eventArgs = new CharacterEventArgs()
            {
                character = (Character)sender
            };
            SetBindCharacterHandler?.Invoke(this, eventArgs);
        }

        public void FreezeCharacterCall(object sender)
        {
            CharacterEventArgs eventArgs = new CharacterEventArgs()
            {
                character = (Character)sender
            };
            FreezeCharacterHandler?.Invoke(this, eventArgs);
        }

        public void SetRigPathCall(object sender)
        {
            ConfigManager configManager = new ConfigManager();
            ProjectConfig projectConfig = (ProjectConfig)configManager.GetCategory(SettingsCategories.PROJECT);

            using (var folderDialog = new FolderBrowserDialog())
            {
                string contentRoot = Environment.GetEnvironmentVariable("CONTENT_ROOT");
                folderDialog.Description = "Pick Folder";
                string rootFolder = projectConfig.CharacterFolder != null ? Path.Combine(contentRoot, projectConfig.CharacterFolder): contentRoot;
                folderDialog.SelectedPath = rootFolder;
                DialogResult result = folderDialog.ShowDialog();

                if (result == DialogResult.OK && !string.IsNullOrWhiteSpace(folderDialog.SelectedPath))
                {
                    CharacterFileEventArgs eventArgs = new CharacterFileEventArgs()
                    {
                        character = (Character)sender,
                        filePath = folderDialog.SelectedPath.Replace(Path.DirectorySeparatorChar, '/')
                    };
                    SetRigPathHandler?.Invoke(this, eventArgs);
                }
            }
        }

        public void DeleteCharacterCall(object sender)
        {
            CharacterEventArgs eventArgs = new CharacterEventArgs()
            {
                character = (Character)sender
            };
            DeleteCharacterHandler?.Invoke(this, eventArgs);
            UpdateRiggerUI();
        }

        public void QuickFKCharacterCall(object sender)
        {
            CharacterEventArgs eventArgs = new CharacterEventArgs()
            {
                character = (Character)sender
            };
            QuickFKCharacterHandler?.Invoke(this, eventArgs);
            UpdateRiggerUI();
        }

        public void RigBuilderCall(object sender)
        {
            RigBuilderHandler?.Invoke(this, null);
        }

        public void ColorSetsCall(object sender)
        {
            ColorSetsHandler?.Invoke(this, null);
        }

        public void SaveRiggingCall(object sender)
        {
            FilePathEventArgs fetchEventArgs = new FilePathEventArgs();
            GetStartingDirectoryHandler?.Invoke(this, fetchEventArgs);

            using (SaveFileDialog filesDialog = new SaveFileDialog())
            {
                filesDialog.Title = "Save Rigging File";
                filesDialog.Filter = "JSON file (*.json)|*.json";
                filesDialog.InitialDirectory = fetchEventArgs.filePath;
                filesDialog.RestoreDirectory = true;

                DialogResult fileResult = filesDialog.ShowDialog();
                if (fileResult == DialogResult.OK)
                {
                    FilePathEventArgs eventArgs = new FilePathEventArgs()
                    {
                        filePath = filesDialog.FileName
                    };
                    SaveRiggingHandler?.Invoke(this, eventArgs);
                }
            }
        }

        public void LoadRiggingCall(object sender)
        {
            FilePathEventArgs fetchEventArgs = new FilePathEventArgs();
            GetStartingDirectoryHandler?.Invoke(this, fetchEventArgs);

            using (OpenFileDialog filesDialog = new OpenFileDialog())
            {
                filesDialog.Title = "Load Rigging File";
                filesDialog.Filter = "JSON file (*.json)|*.json";
                filesDialog.InitialDirectory = fetchEventArgs.filePath;
                filesDialog.RestoreDirectory = true;

                DialogResult fileResult = filesDialog.ShowDialog();
                if (fileResult == DialogResult.OK)
                {
                    FilePathEventArgs eventArgs = new FilePathEventArgs()
                    {
                        filePath = filesDialog.FileName
                    };
                    LoadRiggingHandler?.Invoke(this, eventArgs);
                    UpdateRiggerInPlace();
                }
            }
        }

        public void ExportEventCall(object sender)
        {
            ExportAllHandler?.Invoke(this, null);
        }

        public void ExporterUICall(object sender)
        {
            ExporterUiHandler?.Invoke(this, null);
        }

        public void LoadSettingsCall(object sender)
        {
            SettingsEventArgs eventArgs = new SettingsEventArgs()
            {
                character = (Character)sender,
                preset = SelectedPreset.ToUpper()
            };
            LoadSettingsHandler?.Invoke(this, eventArgs);
        }

        public void SaveSettingsCall(object sender)
        {
            SettingsEventArgs eventArgs = new SettingsEventArgs()
            {
                character = (Character)sender,
                preset = SelectedPreset.ToUpper(),
                incrementVersion = IncrementVersion
            };
            SaveSettingsHandler?.Invoke(this, eventArgs);
        }

        public void SaveUE4SettingsCall(object sender)
        {
            SettingsEventArgs eventArgs = new SettingsEventArgs()
            {
                character = (Character)sender,
                preset = SelectedPreset.ToUpper()
            };
            SaveUE4SettingsHandler?.Invoke(this, eventArgs);
        }

        public void RigRegionEventCall(object sender)
        {
            ActiveCharacter.RigRegionCall(SelectedRigType, IsWorldSpace);
        }

        public void OpenRegionEditorEventCall(object sender)
        {
            OpenRegionEditorHandler?.Invoke(this, null);
        }
        #endregion


        #region EventArgs
        public class SelectEventArgs : EventArgs
        {
            public bool doAdd = false;
        }

        public class SaveIntEventArgs : EventArgs
        {
            public string name = "";
            public int value = 0;
            public string category = "";
        }

        public class SaveBoolEventArgs : EventArgs
        {
            public string name = "";
            public bool value = false;
            public string category = "";
        }

        public class StringEventArgs : EventArgs
        {
            public string stringName = "";
        }

        public class FilePathEventArgs : EventArgs
        {
            public string filePath = "";
        }

        public class CharacterEventArgs : EventArgs
        {
            public Character character = null;
        }

        public class SelectionEventArgs : EventArgs
        {
            public Character character = null;
            public bool animated = true;
        }

        public class CharacterListEventArgs : EventArgs
        {
            public List<string> characterList = null;
        }

        public class CharacterFileEventArgs : EventArgs
        {
            public Character character = null;
            public string filePath = "";
        }

        public class TransferEventArgs : EventArgs
        {
            public Character sourceCharacter = null;
            public Character destinationCharacter = null;
        }

        public class UpdateCharacterEventArgs : EventArgs
        {
            public Character character = null;
            public bool updated = false;
        }

        public class SettingsEventArgs : EventArgs
        {
            public Character character = null;
            public string preset = "";
            public bool incrementVersion = false;
        }

        public class BakeRangeEventArgs : EventArgs
        {
            public bool[] BakeRange = new bool[] { };
        }

        public class ComponentsEventArgs : EventArgs
        {
            public bool IsVisible = true;
            public List<Component> ComponentList = new List<Component>();
        }

        public class CreateButtonEventArgs : EventArgs
        {
            public SelectBarButton SelectButton = null;
        }

        public class SelectButtonEventArgs : EventArgs
        {
            public List<SelectBarButton> SelectButtonList = null;
        }
        #endregion
    }
}