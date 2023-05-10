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

namespace Freeform.Rigging.DCCAssetExporter
{
    using System;
    using System.Timers;
    using System.Collections;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.Collections.Specialized;
    using System.ComponentModel;
    using System.Linq;
    using System.Windows.Forms;
    using System.Threading.Tasks;
    using System.Diagnostics;

    using Freeform.Core.UI;
    using Freeform.Core.Helpers;
    using Freeform.Rigging;
    using System.Windows.Data;
    using System.Windows;
    using System.Windows.Media;
    using System.Windows.Input;

    class DCCAssetExporterVM : ViewModelBase
    {
        public Process ParentProcess;

        public event EventHandler AutoSetupHandler;
        public event EventHandler UpdateHandler;
        public event EventHandler DefinitionSelectedHandler;
        public event EventHandler AssetSelectedHandler;
        public event EventHandler CreateNewDefinitionHandler;
        public event EventHandler AnimationCurveHandler;
        public event EventHandler RemoveRootAnimationHandler;
        public event EventHandler ZeroCharacterHandler;
        public event EventHandler ZeroCharacterRotateHandler;
        public event EventHandler RotationCurveHandler;
        public event EventHandler ZeroMocapHandler;
        public event EventHandler CreateNewAssetHandler;
        public event EventHandler RemoveDefinitionHandler;
        public event EventHandler RemovePropertyHandler;
        public event EventHandler RemoveAssetHandler;
        public event EventHandler ExportWrapperStartHandler;
        public event EventHandler ExportWrapperEndHandler;
        public event EventHandler SaveSettingHandler;

        public event EventHandler WindowActivatedHandler;
        public event EventHandler WindowDeactivatedHandler;


        public RelayCommand AutoSetupCommand { get; set; }
        public RelayCommand ExportCommand { get; set; }
        public RelayCommand CreateNewDefinitionCommand { get; set; }
        public RelayCommand AnimationCurveCommand { get; set; }
        public RelayCommand RemoveRootAnimationCommand { get; set; }
        public RelayCommand ZeroCharacterCommand { get; set; }
        public RelayCommand ZeroCharacterRotateCommand { get; set; }
        public RelayCommand RotationCurveCommand { get; set; }
        public RelayCommand ZeroMocapCommand { get; set; }
        public RelayCommand RemovePropertyCommand { get; set; }
        public RelayCommand CreateNewAssetCommand { get; set; }
        public RelayCommand RemoveDefinitionCommand { get; set; }
        public RelayCommand ExportDefinitionCommand { get; set; }
        public RelayCommand RemoveAssetCommand { get; set; }
        public RelayCommand ExportAssetCommand { get; set; }
        public RelayCommand SwapAssetCommand { get; set; }

        public RelayCommand MoveGroupCommand { get; set; }
        public RelayCommand MoveAssetCommand { get; set; }
        public RelayCommand SetDefinitionSortOrderCommand { get; set; }
        public RelayCommand SetAssetSortOrderCommand { get; set; }
        public RelayCommand HelpCommand { get; set; }


        int _windowWidth;
        public int WindowWidth
        {
            get { return _windowWidth; }
            set
            {
                _windowWidth = value;
                RaisePropertyChanged("WindowWidth");
            }
        }

        public string ParentProcessName
        {
            get
            {
                string name = "Maya";
                if (ParentProcess.ToString().Contains("3dsmax"))
                {
                    name = "3dsMax";
                }
                return name;
            }
        }

        public bool MaxDisabled
        {
            get { return ParentProcessName != "3dsMax"; }
        }

        public bool MaxEnabled
        {
            get { return ParentProcessName == "3dsMax"; }
        }

        bool _selectSceneObjects;
        public bool SelectSceneObjects
        {
            get { return _selectSceneObjects; }
            set { _selectSceneObjects = value; }
        }

        ObservableCollection<ExportDefinition> _exportDefinitionList;
        public ObservableCollection<ExportDefinition> ExportDefinitionList
        {
            get { return _exportDefinitionList; }
            set
            {
                if (_exportDefinitionList != value)
                {
                    _exportDefinitionList = value;
                    RaisePropertyChanged("ExportDefinitionList");
                }
            }
        }

        public CollectionViewSource ExportDefinitionListViewSource { get; set; }
        string _exportDefinitionFilter;
        public string ExportDefinitionFilter
        {
            get { return _exportDefinitionFilter; }
            set
            {
                _exportDefinitionFilter = value;
                if (!string.IsNullOrEmpty(_exportDefinitionFilter))
                    AddExportDefinitionFilter();

                ExportDefinitionListViewSource.View.Refresh();

                if (!ExportDefinitionListViewSource.View.IsEmpty)
                {
                    var enumerator = ExportDefinitionListViewSource.View.GetEnumerator();
                    enumerator.MoveNext();
                }
            }
        }

        ExportDefinition _selectedDefinition;
        public ExportDefinition SelectedDefinition
        {
            get { return _selectedDefinition; }
            set
            {
                _selectedDefinition = value;
                RaisePropertyChanged("SelectedDefinition");

                if (ParentProcessName == "3dsMax")
                {
                    List<ExportAsset> NoExportList = AssetList.Where(x => !_selectedDefinition.ExportAssetList.Contains(x)).ToList();
                    foreach (ExportAsset asset in NoExportList)
                    {
                        asset.AssetExport = false;
                    }
                    List<ExportAsset> ExportList = AssetList.Where(x => _selectedDefinition.ExportAssetList.Contains(x)).ToList();
                    foreach (ExportAsset asset in ExportList)
                    {
                        asset.AssetExport = true;
                    }
                }

                DefinitionEventArgs eventArgs = new DefinitionEventArgs() { Object = value };
                DefinitionSelectedHandler?.Invoke(this, eventArgs);
            }
        }

        ObservableCollection<ExportAsset> _assetList;
        public ObservableCollection<ExportAsset> AssetList
        {
            get { return _assetList; }
            set
            {
                if (_assetList != value)
                {
                    _assetList = value;
                    RaisePropertyChanged("AssetList");
                }
            }
        }

        public CollectionViewSource AssetListViewSource { get; set; }
        string _exportAssetFilter;
        public string ExportAssetFilter
        {
            get { return _exportAssetFilter; }
            set
            {
                _exportAssetFilter = value;
                if (!string.IsNullOrEmpty(_exportAssetFilter))
                    AddExportAssetFilter();

                AssetListViewSource.View.Refresh();

                if (!AssetListViewSource.View.IsEmpty)
                {
                    var enumerator = AssetListViewSource.View.GetEnumerator();
                    enumerator.MoveNext();
                }
            }
        }

        ExportAsset _selectedAsset;
        public ExportAsset SelectedAsset
        {
            get { return _selectedAsset; }
            set
            {
                _selectedAsset = value;
                RaisePropertyChanged("SelectedAsset");

                if (SelectSceneObjects)
                {
                    AssetEventArgs eventArgs = new AssetEventArgs() { Object = value };
                    AssetSelectedHandler?.Invoke(this, eventArgs);
                }
            }
        }

        ObservableCollection<string> _assetTypeList;
        public ObservableCollection<string> AssetTypeList
        {
            get { return _assetTypeList; }
            set
            {
                if (_assetTypeList != value)
                {
                    _assetTypeList = value;
                    RaisePropertyChanged("AssetTypeList");
                }
            }
        }

        string _selectedAssetType;
        public string SelectedAssetType
        {
            get { return _selectedAssetType; }
            set
            {
                if (_selectedAssetType != value)
                {
                    _selectedAssetType = value;
                    RaisePropertyChanged("SelectedAssetType");
                }
            }
        }

        public DCCAssetExporterVM()
        {
            AutoSetupCommand = new RelayCommand(AutoSetupCall);
            ExportCommand = new RelayCommand(ExportCall);
            CreateNewDefinitionCommand = new RelayCommand(CreateNewDefinitionCall);
            AnimationCurveCommand = new RelayCommand(AnimationCurveCall);
            RemoveRootAnimationCommand = new RelayCommand(RemoveRootAnimationCall);
            ZeroCharacterCommand = new RelayCommand(ZeroCharacterCall);
            ZeroCharacterRotateCommand = new RelayCommand(ZeroCharacterRotateCall);
            RotationCurveCommand = new RelayCommand(RotationCurveCall);
            ZeroMocapCommand = new RelayCommand(ZeroMocapCall);
            RemovePropertyCommand = new RelayCommand(RemoveExportPropertyCall);
            CreateNewAssetCommand = new RelayCommand(CreateNewAssetCall);
            RemoveDefinitionCommand = new RelayCommand(RemoveDefinitionCall);
            ExportDefinitionCommand = new RelayCommand(ExportDefinitionCall);
            RemoveAssetCommand = new RelayCommand(RemoveAssetCall);
            ExportAssetCommand = new RelayCommand(ExportAssetCall);
            SwapAssetCommand = new RelayCommand(SwapAssetCall);

            MoveGroupCommand = new RelayCommand(MoveGroupCall);
            MoveAssetCommand = new RelayCommand(MoveAssetCall);

            SetDefinitionSortOrderCommand = new RelayCommand(SetDefinitionSortOrderCall);
            SetAssetSortOrderCommand = new RelayCommand(SetAssetSortOrderCall);

            HelpCommand = new RelayCommand(HelpCall);

            ExportDefinitionList = new ObservableCollection<ExportDefinition>();

            ExportDefinitionListViewSource = new CollectionViewSource
            {
                Source = ExportDefinitionList
            };

            ExportDefinitionListViewSource.SortDescriptions.Add(new SortDescription("Index", ListSortDirection.Ascending));

            AssetList = new ObservableCollection<ExportAsset>();

            AssetListViewSource = new CollectionViewSource
            {
                Source = AssetList
            };
            AssetListViewSource.SortDescriptions.Add(new SortDescription("Index", ListSortDirection.Ascending));

            AssetTypeList = new ObservableCollection<string>();
            SelectedAssetType = AssetTypeList.FirstOrDefault();

            WindowWidth = 740;
            SelectSceneObjects = true;
        }

        public void UpdateExporterUI()
        {
            ExportDefinitionList.Clear();
            AssetList.Clear();

            UpdateHandler?.Invoke(this, null);
        }

        public void WindowActivatedCall()
        {
            WindowActivatedHandler?.Invoke(this, null);
        }

        public void WindowsDeactivatedCall()
        {
            WindowDeactivatedHandler?.Invoke(this, null);
        }

        public void AddExportDefinition(ExportDefinition definition)
        {
            ExportDefinitionList.Add(definition);
            definition.DateCreated = DateTime.Now;
            ExportDefinitionListViewSource.View.Refresh();
        }

        public void AddExportAsset(ExportAsset asset)
        {
            AssetList.Add(asset);
            asset.DateCreated = DateTime.Now;
            AssetListViewSource.View.Refresh();
        }

        public void AutoSetupCall(object sender)
        {
            AutoSetupHandler?.Invoke(this, null);
        }

        public void ExportCall(object sender)
        {
            ExportWrapperStartHandler?.Invoke(this, null);
            foreach (ExportDefinition definition in ExportDefinitionList)
            {
                if (definition.DoExport == true)
                {
                    DefinitionEventArgs eventArgs = new DefinitionEventArgs() { Object = definition };
                    SelectedDefinition = definition;
                    foreach (ExportAsset asset in AssetList)
                    {
                        if (asset.AssetExport)
                        {
                            asset.Export(definition);
                        }
                    }
                }
            }
            ExportWrapperEndHandler?.Invoke(this, null);
        }

        public void CreateNewDefinitionCall(object sender)
        {
            DefinitionEventArgs eventArgs = new DefinitionEventArgs();
            CreateNewDefinitionHandler?.Invoke(this, eventArgs);

            if (eventArgs.Object != null)
            {
                eventArgs.Object.Index = ExportDefinitionList.Count;
                AddExportDefinition(eventArgs.Object);
                SelectedDefinition = eventArgs.Object;
            }
        }

        public void CreateNewAssetCall(object sender)
        {
            AssetEventArgs eventArgs = new AssetEventArgs()
            {
                Type = SelectedAssetType
            };
            CreateNewAssetHandler?.Invoke(this, eventArgs);

            if (eventArgs.Object != null)
            {
                eventArgs.Object.Index = AssetList.Count;
                AddExportAsset(eventArgs.Object);
                SelectedAsset = eventArgs.Object;
            }
        }

        public void RemoveDefinitionCall(object sender)
        {
            ExportDefinition definition = sender as ExportDefinition;

            DefinitionEventArgs eventArgs = new DefinitionEventArgs() { Object = definition };
            RemoveDefinitionHandler?.Invoke(this, eventArgs);

            ExportDefinitionList.Remove(definition);
        }

        public void RemoveAssetCall(object sender)
        {
            ExportAsset asset = sender as ExportAsset;

            AssetEventArgs eventArgs = new AssetEventArgs() { Object = asset };
            RemoveAssetHandler?.Invoke(this, eventArgs);

            AssetList.Remove(asset);
        }

        public void ExportDefinitionCall(object sender)
        {
            var definition = sender as ExportDefinition;
            ExportWrapperStartHandler?.Invoke(this, null);
            foreach (ExportAsset asset in AssetList)
            {
                if (asset.AssetExport)
                {
                    asset.Export(definition);
                }
            }
            ExportWrapperEndHandler?.Invoke(this, null);
        }

        public void AnimationCurveCall(object sender)
        {
            var definition = sender as ExportDefinition;
            CreateProperty(definition, AnimationCurveHandler);
        }

        public void RemoveRootAnimationCall(object sender)
        {
            var exportObject = sender as ExportObject;
            CreateProperty(exportObject, RemoveRootAnimationHandler);
        }

        public void ZeroCharacterCall(object sender)
        {
            var asset = sender as ExportObject;
            CreateProperty(asset, ZeroCharacterHandler);
        }

        public void ZeroCharacterRotateCall(object sender)
        {
            var asset = sender as ExportObject;
            CreateProperty(asset, ZeroCharacterRotateHandler);
        }

        public void RotationCurveCall(object sender)
        {
            var asset = sender as ExportAsset;
            CreateProperty(asset, RotationCurveHandler);
        }

        public void ZeroMocapCall(object sender)
        {
            var asset = sender as ExportAsset;
            CreateProperty(asset, ZeroMocapHandler);
        }

        public void CreateProperty(ExportObject exportObject, EventHandler handler)
        {
            ExportPropertyEventArgs eventArgs = new ExportPropertyEventArgs()
            {
                NodeName = exportObject.NodeName
            };

            handler?.Invoke(this, eventArgs);

            if (eventArgs.Object != null)
            {
                exportObject.AddExportProperty(eventArgs.Object);
            }
        }

        public void RemoveExportPropertyCall(object sender)
        {
            var property = sender as ExportProperty;
            ExportPropertyEventArgs eventArgs = new ExportPropertyEventArgs()
            {
                NodeName = property.NodeName
            };
            RemovePropertyHandler?.Invoke(this, eventArgs);

            if (SelectedDefinition.ExportProperties.Contains(property))
            {
                SelectedDefinition.ExportProperties.Remove(property);
            }
            else if (SelectedAsset.ExportProperties.Contains(property))
            {
                SelectedAsset.ExportProperties.Remove(property);
            }
        }

        public void ExportAssetCall(object sender)
        {
            ExportWrapperStartHandler?.Invoke(this, null);
            SelectedAsset.Export(SelectedDefinition);
            ExportWrapperEndHandler?.Invoke(this, null);
        }

        public void SwapAssetCall(object sender)
        {
            SelectedAsset.SwapGeometry();
        }

        public void MoveGroupCall(object sender)
        {
            int modifier = Convert.ToInt16(sender);
            AdjustExportObjectIndex(modifier, SelectedDefinition, ExportDefinitionList.Cast<ExportObject>().ToList());
            ExportDefinitionListViewSource.View.Refresh();
        }

        public void MoveAssetCall(object sender)
        {
            int modifier = Convert.ToInt16(sender);
            AdjustExportObjectIndex(modifier, SelectedAsset, AssetList.Cast<ExportObject>().ToList());
            AssetListViewSource.View.Refresh();
        }

        public void SetDefinitionSortOrderCall(object sender)
        {
            ExportDefinitionListViewSource.SortDescriptions.Clear();
            ExportDefinitionListViewSource.SortDescriptions.Add(new SortDescription((string)sender, ListSortDirection.Ascending));
            SaveSettingHandler?.Invoke(this, new SaveStringEventArgs() { name = "definition_sort", value = (string)sender, category = "ExporterSettings" });
        }

        public void SetAssetSortOrderCall(object sender)
        {
            AssetListViewSource.SortDescriptions.Clear();
            AssetListViewSource.SortDescriptions.Add(new SortDescription((string)sender, ListSortDirection.Ascending));
            SaveSettingHandler?.Invoke(this, new SaveStringEventArgs() { name = "asset_sort", value = (string)sender, category = "ExporterSettings" });
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

            string helpPage = "https://sites.google.com/view/v1freeformtools/home/exporter";
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
            helpPage += pageName.ToLower();
            System.Diagnostics.Process.Start(helpPage);
        }

        private void AdjustExportObjectIndex(int modifier, ExportObject selectedObject, List<ExportObject> objectList)
        {
            if (selectedObject.Index == objectList.Count - 1 && modifier == 1)
            {
                foreach (ExportObject obj in objectList)
                {
                    obj.Index += 1;
                }
                selectedObject.Index = 0;
            }
            else if (selectedObject.Index == 0 && modifier == -1)
            {
                foreach (ExportObject obj in objectList)
                {
                    obj.Index -= 1;
                }
                selectedObject.Index = objectList.Count - 1;
            }
            else
            {
                List<ExportObject> sortedList = objectList.OrderBy(o => o.Index).ToList();
                ExportObject nextObject = sortedList[selectedObject.Index + modifier];
                selectedObject.Index += modifier;
                nextObject.Index -= modifier;
            }
        }

        private void AddExportDefinitionFilter()
        {
            ExportDefinitionListViewSource.Filter -= new FilterEventHandler(ExportFilter);
            ExportDefinitionListViewSource.Filter += new FilterEventHandler(ExportFilter);
        }

        private void ExportFilter(object sender, FilterEventArgs e)
        {
            e.Accepted = false;

            if (string.IsNullOrEmpty(ExportDefinitionFilter))
                e.Accepted = true;

            if (e.Item is ExportDefinition src && e.Accepted == false)
            {
                if (src.Name.Contains(ExportDefinitionFilter))
                    e.Accepted = true;
            }
        }

        private void AddExportAssetFilter()
        {
            AssetListViewSource.Filter -= new FilterEventHandler(AssetFilter);
            AssetListViewSource.Filter += new FilterEventHandler(AssetFilter);
        }

        private void AssetFilter(object sender, FilterEventArgs e)
        {
            e.Accepted = false;

            if (string.IsNullOrEmpty(ExportAssetFilter))
                e.Accepted = true;

            if (e.Item is ExportAsset src && e.Accepted == false)
            {
                if (src.Name.Contains(ExportAssetFilter))
                    e.Accepted = true;
            }
        }

        public class ExportPropertyEventArgs : EventArgs
        {
            public ExportProperty Object = null;
            public string NodeName = null;
        }

        public class DefinitionEventArgs : EventArgs
        {
            public ExportDefinition Object = null;
        }

        public class AssetEventArgs : EventArgs
        {
            public ExportAsset Object = null;
            public string Type = "";
        }

        public class SaveStringEventArgs : EventArgs
        {
            public string name = "";
            public string value = "";
            public string category = "";
        }
    }
}
