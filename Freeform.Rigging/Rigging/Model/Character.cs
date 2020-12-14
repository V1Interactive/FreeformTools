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
    using System;
    using System.Collections.Generic;
    using System.ComponentModel;
    using System.Collections.ObjectModel;
    using System.Linq;
    using System.Windows.Data;
    using Freeform.Core.UI;
    using System.Windows.Forms;

    public class Character : INotifyPropertyChanged
    {
        public event EventHandler RigRegionEventHandler;
        public event EventHandler DeselectHandler;
        public event EventHandler RemovePropAttachmentHandler;
        public event EventHandler SelectAllGroupsHandler;


        public RelayCommand RemovePropAttachmentCommand { get; set; }


        public string NodeName;
        public bool AllowSelectComponent;
        public bool AllowSelectionEvents;
        public bool AddToSelection;

        #region Properties
        string _name;
        public string Name
        {
            get { return _name; }
            set
            {
                if (_name != value)
                {
                    _name = value;
                    RaisePropertyChanged("Name");
                }
            }
        }

        SkeletonRegion _selectedRegion;
        public SkeletonRegion SelectedRegion
        {
            get { return _selectedRegion; }
            set
            {
                if (_selectedRegion != value)
                {
                    _selectedRegion = value;
                    RaisePropertyChanged("SelectedRegion");
                }
            }
        }

        public ObservableCollection<Component> _componentList;
        public ObservableCollection<Component> ComponentList
        {
            get { return _componentList; }
            set
            {
                if (_componentList != value)
                {
                    _componentList = value;
                    RaisePropertyChanged("ComponentList");
                }
            }
        }

        public ObservableCollection<PropAttachment> _propAttachmentList;
        public ObservableCollection<PropAttachment> PropAttachmentList
        {
            get { return _propAttachmentList; }
            set
            {
                if (_propAttachmentList != value)
                {
                    _propAttachmentList = value;
                    RaisePropertyChanged("PropAttachmentList");
                }
            }
        }

        int _propAttachmentIndex;
        public int PropAttachmentIndex
        {
            get { return _propAttachmentIndex; }
            set
            {
                if (_propAttachmentIndex != value)
                {
                    _propAttachmentIndex = value;
                    RaisePropertyChanged("PropAttachmentIndex");
                }
            }
        }

        public CollectionViewSource ComponentGroupViewSource { get; set; }
        public ObservableCollection<ComponentGroup> _ComponentGroupCollection;
        public ObservableCollection<ComponentGroup> ComponentGroupCollection
        {
            get { return _ComponentGroupCollection; }
            set
            {
                if (_ComponentGroupCollection != value)
                {
                    _ComponentGroupCollection = value;
                    RaisePropertyChanged("ComponentGroupCollection");
                }
            }
        }


        public List<Component> SelectedComponentList
        {
            get { return ComponentList.Cast<Component>().Where(x => x.IsSelected && x.Enabled).ToList(); }
        }

        readonly Component _selectedComponent;
        public Component SelectedComponent
        {
            get { return _selectedComponent; }
            set
            {
                if(AllowSelectComponent == true)
                {
                    if (value != null)
                    {
                        if (Control.ModifierKeys != Keys.Shift && System.Windows.Forms.Control.ModifierKeys != Keys.Control && !AddToSelection)
                        {
                                DeselectAll();
                        }

                        if (value.LockedState != "locked")
                        {
                            value.RunSelectionEvent = AllowSelectionEvents;
                            value.IsSelected = true;
                            value.RunSelectionEvent = true;
                        }
                    }
                    else
                    {
                        DeselectAll();
                    }

                    RaisePropertyChanged("SelectedComponent");
                }
            }
        }


        string _componentSearchFilter;
        public string ComponentSearchFilter
        {
            get { return _componentSearchFilter; }
            set
            {
                _componentSearchFilter = value;
                UpdateFilteredLists();
            }
        }

        public ObservableCollection<SkeletonRegion> _regionList;
        public ObservableCollection<SkeletonRegion> RegionList
        {
            get { return _regionList; }
            set
            {
                if (_regionList != value)
                {
                    _regionList = value;
                    RaisePropertyChanged("Regions");
                }
            }
        }

        public CollectionViewSource RegionViewSource { get; set; }
        string _regionSearchFilter;
        public string RegionSearchFilter
        {
            get { return _regionSearchFilter; }
            set
            {
                _regionSearchFilter = value;
                if (!string.IsNullOrEmpty(_regionSearchFilter))
                    RigRegionFilter();

                RegionViewSource.View.Refresh();

                if (!RegionViewSource.View.IsEmpty)
                {
                    var enumerator = RegionViewSource.View.GetEnumerator();
                    enumerator.MoveNext();
                    SelectedRegion = enumerator.Current as SkeletonRegion;
                }
            }
        }
        #endregion

        bool _outOfDate;
        public bool OutOfDate
        {
            get { return _outOfDate; }
            set
            {
                _outOfDate = value;

                if (!value) { IsSelected = IsSelected; }

                RaisePropertyChanged("OutOfDate");
            }
        }

        bool _rigAllFiltered;
        public bool RigAllFiltered
        {
            get { return _rigAllFiltered; }
            set
            {
                if (_rigAllFiltered != value)
                {
                    _rigAllFiltered = value;
                    RaisePropertyChanged("RigAllFiltered");
                }
            }
        }

        public readonly string DefaultUpdateMessage = "Up to date";
        string _updateMessage;
        public string UpdateMessage
        {
            get { return _updateMessage; }
            set
            {
                _updateMessage = value;
                RaisePropertyChanged("UpdateMessage");
            }
        }

        string _buttonStyle;
        public string ButtonStyle
        {
            get { return _buttonStyle; }
            set
            {
                _buttonStyle = value;
                RaisePropertyChanged("ButtonStyle");
            }
        }

        bool _isSelected;
        public bool IsSelected
        {
            get { return _isSelected; }
            set
            {
                _isSelected = value;

                ButtonStyle = value ? "SelectedTrimForegroundButton" : "TrimForegroundButton";
                if (OutOfDate) { ButtonStyle = "ErorrTrimForegroundButton"; }
            }
        }


        public Character(string aName, string metaNodeName)
        {
            RemovePropAttachmentCommand = new RelayCommand(RemovePropAttachmentCall);

            Name = aName;
            NodeName = metaNodeName;
            OutOfDate = false;
            RigAllFiltered = false;
            AllowSelectComponent = true;
            AllowSelectionEvents = false;
            AddToSelection = false;
            _selectedComponent = null;
            ButtonStyle = "TrimForegroundButton";
            UpdateMessage = DefaultUpdateMessage;

            ComponentList = new ObservableCollection<Component>();
            PropAttachmentList = new ObservableCollection<PropAttachment>();
            ComponentGroupCollection = new ObservableCollection<ComponentGroup>();

            ComponentGroupViewSource = new CollectionViewSource
            {
                Source = ComponentGroupCollection
            };
            ComponentGroupViewSource.SortDescriptions.Add(new SortDescription("Name", ListSortDirection.Ascending));

            AddComponentGroup("Miscellaneous");

            RegionList = new ObservableCollection<SkeletonRegion>();
            RegionViewSource = new CollectionViewSource
            {
                Source = RegionList
            };

            ComponentSearchFilter = "";
        }


        public ComponentGroup GetComponentGroup(string name)
        {
            return ComponentGroupCollection.Where(group => group.Name == name).FirstOrDefault();
        }

        public void AddComponentGroup(string name)
        {
            if (GetComponentGroup(name) == null)
            {
                ComponentGroup componentGroup = new ComponentGroup(name);
                componentGroup.ViewSource.Source = ComponentList;

                ComponentGroupCollection.Add(componentGroup);
            }
        }

        public void AddComponent(Component component)
        {
            AddComponentGroup(component.GroupName);

            ComponentList.Add(component);
            UpdateFilteredLists();
        }

        public void RemoveComponent(Component component)
        {
            if(component != null)
            {
                ComponentList.Remove(component);
                UpdateGroupCollection();
            }
        }

        public void ClearComponentList()
        {
            ComponentList.Clear();
            UpdateGroupCollection();
        }

        public void UpdateGroupCollection()
        {
            string tempFilterText = ComponentSearchFilter;
            ComponentSearchFilter = "";

            for (int i = ComponentGroupCollection.Count - 1; i >= 0; i--)
            {
                if (ComponentGroupCollection[i].Name != "Miscellaneous" && ComponentGroupCollection[i].ViewSource.View.IsEmpty)
                {
                    ComponentGroupCollection.RemoveAt(i);
                }
            }

            ComponentSearchFilter = tempFilterText;
        }

        public Component GetComponent(string nodeName)
        {
            foreach(Component comp in ComponentList)
            {
                if(comp.NodeName == nodeName) { return comp; }
            }
            return null;
        }

        public void DeselectAll()
        {
            AllowSelectComponent = false;
            foreach (Component deselectComponent in SelectedComponentList)
            {
                deselectComponent.RunSelectionEvent = AllowSelectionEvents;
                deselectComponent.IsSelected = false;
                deselectComponent.RunSelectionEvent = true;
            }
            if(AllowSelectionEvents == true)
                DeselectHandler?.Invoke(this, null);

            AllowSelectComponent = true;
        }

        public void SelectAllGroupsCall()
        {
            // Roundabout way to call SelectAllGroups encapsulated in a Maya undo block
            // SelectAllGroupsCall() -> Character SelectAllGroupsHandler() -> python select_all_groups() -> Character SelectAllGroups()
            SelectAllGroupsHandler?.Invoke(this, null);
        }

        public void SelectAllGroups()
        {
            if (Control.ModifierKeys != Keys.Shift && Control.ModifierKeys != Keys.Control)
            {
                DeselectAll();
            }

            foreach (ComponentGroup componentGroup in ComponentGroupCollection)
            {
                SelectGroup(componentGroup, true);
            }
        }

        public void SelectGroup(ComponentGroup componentGroup, bool forceAdd)
        {
            if (Control.ModifierKeys != Keys.Shift && Control.ModifierKeys != Keys.Control && forceAdd != true)
            {
                DeselectAll();
            }

            AllowSelectComponent = false;
            foreach (Component item in componentGroup.ViewSource.View)
            {
                if(item.LockedState != "locked")
                {
                    item.RunSelectionEvent = AllowSelectionEvents;
                    item.AddToSelection = true;
                    item.IsSelected = true;
                    item.AddToSelection = false;
                    item.RunSelectionEvent = true;
                }
            }
            AllowSelectComponent = true;
        }

        public void RigRegionCall(List<string> rigTypeName, bool isWorldSpaceArg)
        {
            List<SkeletonRegion> regionList = new List<SkeletonRegion>();

            regionList = RigAllFiltered ? RegionViewSource.View.Cast<SkeletonRegion>().ToList() : new List<SkeletonRegion>() { SelectedRegion };

            foreach(SkeletonRegion region in regionList)
            {
                RigRegionEventArgs eventArgs = new RigRegionEventArgs()
                {
                    skeletonRegion = region,
                    rigType = rigTypeName,
                    isWorldSpace = isWorldSpaceArg
                };

                RigRegionEventHandler?.Invoke(this, eventArgs);
            }
        }

        public void RemovePropAttachmentCall(object sender)
        {
            PropAttachment propAttachment = (PropAttachment)sender;
            PropAttachmentList.Remove(propAttachment);

            PropAttachmentEventArgs eventArgs = new PropAttachmentEventArgs()
            {
                PropAttachment = propAttachment
            };
            RemovePropAttachmentHandler?.Invoke(this, eventArgs);
        }


        #region EventArgs
        public class PropAttachmentEventArgs : EventArgs
        {
            public PropAttachment PropAttachment = null;
        }

        public class SelectEventArgs : EventArgs
        {
            public bool doAdd = false;
        }

        public class RigRegionEventArgs : EventArgs
        {
            public SkeletonRegion skeletonRegion = null;
            public List<string> rigType = null;
            public bool isWorldSpace = false;
        }

        public class AddRegionEventArgs : EventArgs
        {
            public string side = "";
            public string region = "";
            public string root = "";
            public string end = "";
            public bool success = false;
        }
        #endregion


        public void UpdateFilteredLists()
        {
            AddComponentFilter();

            foreach (ComponentGroup componentGroup in ComponentGroupCollection)
            {
                componentGroup.UpdateViewSource();
            }
        }

        private void AddComponentFilter()
        {
            foreach (ComponentGroup componentGroup in ComponentGroupCollection)
            {
                componentGroup.ViewSource.Filter -= new FilterEventHandler(ComponentFilter);
                componentGroup.ViewSource.Filter -= new FilterEventHandler(componentGroup.ComponentFilter);
                componentGroup.ViewSource.Filter += new FilterEventHandler(ComponentFilter);
                componentGroup.ViewSource.Filter += new FilterEventHandler(componentGroup.ComponentFilter);
            }
        }

        private void ComponentFilter(object sender, FilterEventArgs e)
        {
            e.Accepted = false;

            string[] sideRegionSplit = ComponentSearchFilter.Split(null);
            string side = sideRegionSplit[0].ToLower();
            string region = string.Empty;
            if (sideRegionSplit.Length > 1)
                region = sideRegionSplit[1].ToLower();

            bool singleEntry = sideRegionSplit.Length <= 1;

            if (string.IsNullOrEmpty(side) && singleEntry)
                e.Accepted = true;

            if (e.Item is Component src && e.Accepted == false)
            {
                if (singleEntry)
                {
                    if (src.Side.ToLower().Contains(side) || src.Region.ToLower().Contains(side) || src.Type.ToLower().Contains(side) || src.GroupName.ToLower() == side)
                        e.Accepted = true;
                }
                else
                {
                    if (src.Side.ToLower().Contains(side) && (src.Region.ToLower().Contains(region) || src.GroupName.ToLower() == region))
                        e.Accepted = true;
                }
            }
        }

        private void RigRegionFilter()
        {
            RegionViewSource.Filter -= new FilterEventHandler(RegionsFilter);
            RegionViewSource.Filter += new FilterEventHandler(RegionsFilter);
        }

        private void RegionsFilter(object sender, FilterEventArgs e)
        {
            e.Accepted = false;

            string[] sideRegionSplit = RegionSearchFilter.Split(null);
            string side = sideRegionSplit[0];
            string region = string.Empty;
            if (sideRegionSplit.Length > 1)
                region = sideRegionSplit[1];

            bool singleEntry = sideRegionSplit.Length <= 1;

            if (string.IsNullOrEmpty(side) && singleEntry)
                e.Accepted = true;

            if (e.Item is SkeletonRegion src && e.Accepted == false)
            {
                if (singleEntry)
                {
                    if (src.Side.ToLower().Contains(side.ToLower()) || src.Region.ToLower().Contains(side.ToLower()))
                        e.Accepted = true;
                }
                else
                {
                    if (src.Side.ToLower().Contains(side.ToLower()) && src.Region.ToLower().Contains(region.ToLower()))
                        e.Accepted = true;
                }
            }
        }

        void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}
