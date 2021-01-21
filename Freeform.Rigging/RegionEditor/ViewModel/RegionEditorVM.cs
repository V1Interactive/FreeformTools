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

namespace Freeform.Rigging.RegionEditor
{
    using System;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.ComponentModel;
    using System.Linq;
    using System.Windows;
    using System.Windows.Controls;
    using System.Windows.Data;
    using System.Windows.Forms;
    using System.Windows.Input;
    using System.Windows.Media;
    using Freeform.Core.UI;

    public class RegionEditorVM : ViewModelBase
    {
        public event EventHandler PickEventHandler;
        public event EventHandler AddRegionEventHandler;
        public event EventHandler RemoveRegionEventHandler;
        public event EventHandler SideChangedEventHandler;
        public event EventHandler RegionChangedEventHandler;
        public event EventHandler GroupChangedEventHandler;
        public event EventHandler RootChangedEventHandler;
        public event EventHandler EndChangedEventHandler;
        public event EventHandler SelectionChangedEventHandler;
        public event EventHandler CheckSelectionEventHandler;
        public event EventHandler MirrorFilteredRegionsHandler;

        public RelayCommand PickCommand { get; set; }
        public RelayCommand AddRegionCommand { get; set; }
        public RelayCommand RemoveRegionCommand { get; set; }
        public RelayCommand ClearSelectionCommand { get; set; }
        public RelayCommand MirrorFilteredRegionCommand { get; set; }
        public RelayCommand HelpCommand { get; set; }

        bool checkRootEndConnection = true;

        ObservableCollection<Region> _regionList;
        public ObservableCollection<Region> RegionList
        {
            get { return _regionList; }
            set
            {
                if (_regionList != value)
                {
                    _regionList = value;
                    RaisePropertyChanged("RegionList");
                }
            }
        }

        public CollectionViewSource RegionListViewSource { get; set; }
        string _regionFilter;
        public string RegionSearchFilter
        {
            get { return _regionFilter; }
            set
            {
                _regionFilter = value;
                if (!string.IsNullOrEmpty(_regionFilter))
                    AddRegionFilter();

                RegionListViewSource.View.Refresh();

                if (!RegionListViewSource.View.IsEmpty)
                {
                    var enumerator = RegionListViewSource.View.GetEnumerator();
                    enumerator.MoveNext();
                }
            }
        }

        string _mirrorReplaceText;
        public string MirrorReplaceText
        {
            get { return _mirrorReplaceText; }
            set
            {
                _mirrorReplaceText = value;
                RaisePropertyChanged("MirrorReplaceText");
            }
        }

        string _mirrorReplaceWithText;
        public string MirrorReplaceWithText
        {
            get { return _mirrorReplaceWithText; }
            set
            {
                _mirrorReplaceWithText = value;
                RaisePropertyChanged("MirrorReplaceWithText");
            }
        }

        string _jointReplaceText;
        public string JointReplaceText
        {
            get { return _jointReplaceText; }
            set
            {
                _jointReplaceText = value;
                RaisePropertyChanged("JointReplaceText");
            }
        }

        string _jointReplaceWithText;
        public string JointReplaceWithText
        {
            get { return _jointReplaceWithText; }
            set
            {
                _jointReplaceWithText = value;
                RaisePropertyChanged("JointReplaceWithText");
            }
        }

        Region _selectedRegionItem;
        public Region SelectedRegionItem
        {
            get { return _selectedRegionItem; }
            set
            {
                if (_selectedRegionItem != value)
                {
                    _selectedRegionItem = value;
                    checkRootEndConnection = false;
                    if (SelectedRegionItem != null)
                    {
                        RegionIsSelected = true;
                        RegionIsNull = false;
                        Side = SelectedRegionItem.Side;
                        Region = SelectedRegionItem.Name;
                        Group = SelectedRegionItem.Group;
                        Root = SelectedRegionItem.Root;
                        End = SelectedRegionItem.End;
                    }
                    else
                    {
                        RegionIsSelected = false;
                        RegionIsNull = true;
                        Side = "";
                        Region = "";
                        Group = "";
                        Root = "";
                        End = "";
                    }
                    checkRootEndConnection = true;
                    if(HighlightRegions == true)
                    {
                        SelectionChangedEventHandler?.Invoke(this, new RegionEventArgs() { Region = SelectedRegionItem, Success = HighlightRegions });
                    }

                    if(value != null)
                    {
                        RegionEventArgs riggedCheckArgs = new RegionEventArgs() { Region = SelectedRegionItem, Success = false };
                        CheckSelectionEventHandler?.Invoke(this, riggedCheckArgs);
                        SelectionNotRigged = riggedCheckArgs.Success;
                    }
                    else
                    {
                        SelectionNotRigged = true;
                    }
                    
                    RaisePropertyChanged("SelectedRegionItem");
                }
            }
        }

        bool _selectionIsRigged;
        public bool SelectionNotRigged
        {
            get { return _selectionIsRigged; }
            set
            {
                if (_selectionIsRigged != value)
                {
                    _selectionIsRigged = value;
                    RaisePropertyChanged("SelectionNotRigged");
                }
            }
        }

        bool _highlightRegions;
        public bool HighlightRegions
        {
            get { return _highlightRegions; }
            set
            {
                if (_highlightRegions != value)
                {
                    _highlightRegions = value;
                    RaisePropertyChanged("HighlightRegions");
                }
            }
        }

        bool _regionIsSelected;
        public bool RegionIsSelected
        {
            get { return _regionIsSelected; }
            set
            {
                if (_regionIsSelected != value)
                {
                    _regionIsSelected = value;
                    GridStyle = value ? "SelectedGrid" : "V1Grid";
                    TextStyle = value ? "DarkTextBlock" : "LightTextBlock";
                    RaisePropertyChanged("RegionIsSelected");
                }
            }
        }

        bool _regionIsNull;
        public bool RegionIsNull
        {
            get { return _regionIsNull; }
            set
            {
                if (_regionIsNull != value)
                {
                    _regionIsNull = value;
                    RaisePropertyChanged("RegionIsNull");
                }
            }
        }

        string _characterName;
        public string CharacterName
        {
            get { return _characterName; }
            set
            {
                if (_characterName != value)
                {
                    _characterName = value;
                    if (SelectedRegionItem != null)
                    {
                        SelectedRegionItem.Side = value;
                    }
                    RaisePropertyChanged("CharacterName");
                }
            }
        }

        string _side;
        public string Side
        {
            get { return _side; }
            set
            {
                if (_side != value)
                {
                    _side = value;
                    if(SelectedRegionItem != null)
                    {
                        SideChangedEventHandler?.Invoke(this, new RegionEventArgs() { Region = SelectedRegionItem, Value = value });
                        SelectedRegionItem.Side = value;
                    }
                    RaisePropertyChanged("Side");
                }
            }
        }

        string _region;
        public string Region
        {
            get { return _region; }
            set
            {
                if (_region != value)
                {
                    _region = value;
                    if (SelectedRegionItem != null)
                    {
                        RegionChangedEventHandler?.Invoke(this, new RegionEventArgs() { Region = SelectedRegionItem, Value = value });
                        SelectedRegionItem.Name = value;
                    }
                    RaisePropertyChanged("Region");
                }
            }
        }

        string _group;
        public string Group
        {
            get { return _group; }
            set
            {
                if (_group != value)
                {
                    _group = value;
                    if (SelectedRegionItem != null)
                    {
                        GroupChangedEventHandler?.Invoke(this, new RegionEventArgs() { Region = SelectedRegionItem, Value = value });
                        SelectedRegionItem.Group = value;
                    }
                    RaisePropertyChanged("Group");
                }
            }
        }

        string _root;
        public string Root
        {
            get { return _root; }
            set
            {
                if (_root != value)
                {
                    if (SelectedRegionItem != null && checkRootEndConnection == true)
                    {
                        RegionEventArgs eventArgs = new RegionEventArgs() { Region = SelectedRegionItem, Value = value };
                        RootChangedEventHandler?.Invoke(this, eventArgs);
                        if (eventArgs.Success == true)
                        {
                            SelectedRegionItem.Root = value;
                            _root = value;
                            RaisePropertyChanged("Root");
                        }
                    }
                    else
                    {
                        _root = value;
                        RaisePropertyChanged("Root");
                    }

                    if (HighlightRegions == true)
                    {
                        SelectionChangedEventHandler?.Invoke(this, new RegionEventArgs() { Region = SelectedRegionItem, Success = HighlightRegions });
                    }
                }
            }
        }

        string _end;
        public string End
        {
            get { return _end; }
            set
            {
                if (_end != value)
                {
                    if (SelectedRegionItem != null && checkRootEndConnection == true)
                    {
                        RegionEventArgs eventArgs = new RegionEventArgs() { Region = SelectedRegionItem, Value = value };
                        EndChangedEventHandler?.Invoke(this, eventArgs);
                        if (eventArgs.Success == true)
                        {
                            SelectedRegionItem.End = value;
                            _end = value;
                            RaisePropertyChanged("End");
                        }
                    }
                    else
                    {
                        _end = value;
                        RaisePropertyChanged("End");
                    }

                    if (HighlightRegions == true)
                    {
                        SelectionChangedEventHandler?.Invoke(this, new RegionEventArgs() { Region = SelectedRegionItem, Success = HighlightRegions });
                    }
                }
            }
        }

        string _gridStyle;
        public string GridStyle
        {
            get { return _gridStyle; }
            set
            {
                _gridStyle = value;
                RaisePropertyChanged("GridStyle");
            }
        }

        string _textStyle;
        public string TextStyle
        {
            get { return _textStyle; }
            set
            {
                _textStyle = value;
                RaisePropertyChanged("TextStyle");
            }
        }


        public RegionEditorVM()
        {
            MirrorReplaceText = "left";
            MirrorReplaceWithText = "right";
            JointReplaceText = "_l";
            JointReplaceWithText = "_r";

            Side = "";
            Region = "";
            Group = "";
            Root = "";
            End = "";
            GridStyle = "V1Grid";
            TextStyle = "LightTextBlock";
            SelectionNotRigged = true;

            PickCommand = new RelayCommand(PickEventCall);
            AddRegionCommand = new RelayCommand(AddRegionEventCall);
            RemoveRegionCommand = new RelayCommand(RemoveRegionEventCall);
            ClearSelectionCommand = new RelayCommand(ClearSelectionEventCall);
            MirrorFilteredRegionCommand = new RelayCommand(MirrorFilteredRegionCall);
            HelpCommand = new RelayCommand(HelpCall);

            RegionList = new ObservableCollection<Region>();
            RegionListViewSource = new CollectionViewSource
            {
                Source = RegionList
            };
            RegionListViewSource.SortDescriptions.Add(new SortDescription("Side", ListSortDirection.Ascending));
            RegionListViewSource.SortDescriptions.Add(new SortDescription("Name", ListSortDirection.Ascending));

            RegionIsNull = true;
        }



        public void AddRegion(string side, string name, string group, string root, string end)
        {
            RegionList.Add(new Region(side, name, group, root, end));
        }


        public void SetSelectedRoot(string root)
        {
            SelectedRegionItem.Root = root;
        }

        public void PickEventCall(object sender)
        {
            StringEventArgs eventArgs = new StringEventArgs()
            {
                StringName = sender.ToString()
            };
            PickEventHandler?.Invoke(this, eventArgs);
        }

        public void AddRegionEventCall(object sender)
        {
            RegionEventArgs eventArgs = new RegionEventArgs()
            {
                Region = new Region(Side, Region, Group, Root, End)
            };
            AddRegionEventHandler?.Invoke(this, eventArgs);

            if (eventArgs.Success == true)
            {
                RegionList.Add(eventArgs.Region);
                Root = "";
                End = "";
            }
        }

        public void RemoveRegionEventCall(object sender)
        {
            RegionEventArgs eventArgs = new RegionEventArgs()
            {
                Region = SelectedRegionItem
            };
            RemoveRegionEventHandler?.Invoke(this, eventArgs);

            if (eventArgs.Success == true)
            {
                RegionList.Remove(eventArgs.Region);
            }
        }

        public void ClearSelectionEventCall(object sender)
        {
            SelectedRegionItem = null;
            Side = "";
            Region = "";
            Group = "";
            Root = "";
            End = "";
        }

        public void MirrorFilteredRegionCall(object sender)
        {
            List<Region> NewRegionList = new List<Region>();
            foreach(Region region in RegionListViewSource.View)
            {
                if (region.Side.Contains(MirrorReplaceText))
                {
                    MirrorRegionEventArgs eventArgs = new MirrorRegionEventArgs()
                    {
                        Region = region,
                        Replace = MirrorReplaceText,
                        ReplaceWith = MirrorReplaceWithText,
                        JointReplace = JointReplaceText,
                        JointReplaceWith = JointReplaceWithText
                    };
                    MirrorFilteredRegionsHandler?.Invoke(this, eventArgs);

                    if (eventArgs.NewRegion != null)
                    {
                        NewRegionList.Add(eventArgs.NewRegion);
                    }
                }
            }

            foreach(Region newRegion in NewRegionList)
            {
                RegionList.Add(newRegion);
            }
        }

        public void HelpCall(object sender)
        {
            var hit = VisualTreeHelper.HitTest((UIElement)sender, Mouse.GetPosition((UIElement)sender));
            var item = hit?.VisualHit;

            while (item != null)
            {
                // Exit if we find a valid Tag
                if (item is FrameworkElement itemElement && itemElement.Tag != null)
                    break;
                item = VisualTreeHelper.GetParent(item);
            }

            string helpPage = "https://sites.google.com/view/v1freeformtools/home/rigging/regions";
            string pageName = "";

            if (item == null)
            {
                // Do Nothing with the page name
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
            helpPage = helpPage + pageName.ToLower();
            System.Diagnostics.Process.Start(helpPage);
        }

        private void AddRegionFilter()
        {
            RegionListViewSource.Filter -= new FilterEventHandler(RegionsFilter);
            RegionListViewSource.Filter += new FilterEventHandler(RegionsFilter);
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

            if (e.Item is Region src && e.Accepted == false)
            {
                if (singleEntry)
                {
                    if (src.Side.ToLower().Contains(side.ToLower()) || src.Name.ToLower().Contains(side.ToLower()))
                        e.Accepted = true;
                }
                else
                {
                    if (src.Side.ToLower().Contains(side.ToLower()) && src.Name.ToLower().Contains(region.ToLower()))
                        e.Accepted = true;
                }
            }
        }


        public class RegionEventArgs : EventArgs
        {
            public Region Region = null;
            public bool Success = false;
            public string Value = "";
        }

        public class StringEventArgs : EventArgs
        {
            public string StringName = "";
        }

        public class MirrorRegionEventArgs : EventArgs
        {
            public Region Region = null;
            public string Replace = "";
            public string ReplaceWith = "";
            public string JointReplace = "";
            public string JointReplaceWith = "";
            public Region NewRegion = null;
        }

        public class BoolEventArgs : EventArgs
        {
            public bool valid = false;
        }
    }
}
