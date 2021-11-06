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


namespace Freeform.Rigging.ExportJointList
{
    using System;
    using System.Timers;
    using System.Collections;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.Collections.Specialized;
    using System.ComponentModel;
    using System.Linq;

    using Freeform.Core.UI;
    using Freeform.Core.Helpers;
    using Freeform.Rigging;
  using System.Windows.Data;

  public class ExportJointListVM : ViewModelBase
    {
        public RelayCommand ToNoExportCommand { get; set; }
        public RelayCommand ToExportCommand { get; set; }

        public event EventHandler SetExportEventHandler;


        ObservableCollection<ExportItem> _noExportList;
        public ObservableCollection<ExportItem> NoExportList
        {
            get { return _noExportList; }
            set
            {
                if (_noExportList != value)
                {
                    _noExportList = value;
                    RaisePropertyChanged("NoExportList");
                }
            }
        }
        public CollectionViewSource NoExportListViewSource { get; set; }
        string _noExportFilter;
        public string NoExportFilter
        {
            get { return _noExportFilter; }
            set
            {
                _noExportFilter = value;
                if (!string.IsNullOrEmpty(_noExportFilter))
                    AddNoExportFilter();

                NoExportListViewSource.View.Refresh();

                if (!NoExportListViewSource.View.IsEmpty)
                {
                    var enumerator = NoExportListViewSource.View.GetEnumerator();
                    enumerator.MoveNext();
                }
            }
        }

        public List<ExportItem> SelectedNoExportList;
        readonly ExportItem _selectedNoExportItem;
        public ExportItem SelectedNoExportItem
        {
            get { return _selectedNoExportItem; }
            set
            {
                if (_selectedNoExportItem != value)
                {
                    // Don't set _selectedRigItem so it stays null for the UI to think the selection is always changed with Extended selection
                    SelectedNoExportList = NoExportList.Cast<ExportItem>().Where(x => x.IsSelected).ToList();
                    RaisePropertyChanged("SelectedNoExportItem");
                }
            }
        }

        ObservableCollection<ExportItem> _exportList;
        public ObservableCollection<ExportItem> ExportList
        {
            get { return _exportList; }
            set
            {
                if (_exportList != value)
                {
                    _exportList = value;
                    RaisePropertyChanged("ExportList");
                }
            }
        }
        public CollectionViewSource ExportListViewSource { get; set; }

        string _exportFilter;
        public string ExportFilter
        {
            get { return _exportFilter; }
            set
            {
                _exportFilter = value;
                if (!string.IsNullOrEmpty(_exportFilter))
                    AddExportFilter();

                ExportListViewSource.View.Refresh();

                if (!ExportListViewSource.View.IsEmpty)
                {
                    var enumerator = ExportListViewSource.View.GetEnumerator();
                    enumerator.MoveNext();
                }
            }
        }


        public List<ExportItem> SelectedExportList;
        readonly ExportItem _selectedExportItem;
        public ExportItem SelectedExportItem
        {
            get { return _selectedExportItem; }
            set
            {
                if (_selectedExportItem != value)
                {
                    // Don't set _selectedRigItem so it stays null for the UI to think the selection is always changed with Extended selection
                    SelectedExportList = ExportList.Cast<ExportItem>().Where(x => x.IsSelected).ToList();
                    RaisePropertyChanged("SelectedRigItem");
                }
            }
        }

        string _selectedItem;
        public string SelectedItem
        {
            get { return _selectedItem; }
            set
            {
                _selectedItem = value;
            }
        }

        public ExportJointListVM()
        {
            NoExportList = new ObservableCollection<ExportItem>();
            NoExportListViewSource = new CollectionViewSource()
            {
                Source = NoExportList
            };
            NoExportListViewSource.SortDescriptions.Add(new SortDescription("Name", ListSortDirection.Descending));
            SelectedNoExportList = new List<ExportItem>();

            ExportList = new ObservableCollection<ExportItem>();
            ExportListViewSource = new CollectionViewSource()
            {
                Source = ExportList
            };
            ExportListViewSource.SortDescriptions.Add(new SortDescription("Name", ListSortDirection.Descending));
            SelectedExportList = new List<ExportItem>();

            _selectedExportItem = null;
            _selectedNoExportItem = null;

            ToNoExportCommand = new RelayCommand(ToNoExportCall);
            ToExportCommand = new RelayCommand(ToExportCall);
        }

        public void AddNoExportItem(string name)
        {
            NoExportList.Add(new ExportItem(name));
        }

        public void AddExportItem(string name)
        {
            ExportList.Add(new ExportItem(name));
        }

        public void ToExportCall(object sender)
        {
            SetExportEventArgs eventArgs = new SetExportEventArgs()
            {
                ExportItemList = SelectedNoExportList,
                doExport = true
            };
            SetExportEventHandler?.Invoke(this, eventArgs);

            foreach(ExportItem item in SelectedNoExportList)
            {
                ExportList.Add(item);
                NoExportList.Remove(item);
                item.IsSelected = false;
            }

            SelectedNoExportList.Clear();
        }

        public void ToNoExportCall(object sender)
        {
            SetExportEventArgs eventArgs = new SetExportEventArgs()
            {
                ExportItemList = SelectedExportList,
                doExport = false
            };
            SetExportEventHandler?.Invoke(this, eventArgs);

            foreach(ExportItem item in SelectedExportList)
            {
                NoExportList.Add(item);
                ExportList.Remove(item);
                item.IsSelected = false;
            }

            SelectedExportList.Clear();
        }


        private void AddNoExportFilter()
        {
            NoExportListViewSource.Filter -= new FilterEventHandler(NoExportFilterCall);
            NoExportListViewSource.Filter += new FilterEventHandler(NoExportFilterCall);
        }

        private void NoExportFilterCall(object sender, FilterEventArgs e)
        {
            e.Accepted = false;

            if (string.IsNullOrEmpty(NoExportFilter))
                e.Accepted = true;


            if (e.Item is ExportItem src && e.Accepted == false)
            {
                if (src.Name.ToLower().Contains(NoExportFilter))
                {
                    e.Accepted = true;
                }
            }
        }

        private void AddExportFilter()
        {
            ExportListViewSource.Filter -= new FilterEventHandler(ExportFilterCall);
            ExportListViewSource.Filter += new FilterEventHandler(ExportFilterCall);
        }

        private void ExportFilterCall(object sender, FilterEventArgs e)
        {
            e.Accepted = false;

            if (string.IsNullOrEmpty(ExportFilter))
                e.Accepted = true;


            if (e.Item is ExportItem src && e.Accepted == false)
            {
                if (src.Name.ToLower().Contains(ExportFilter))
                {
                    e.Accepted = true;
                }
            }
        }

        public class SetExportEventArgs : EventArgs
        {
            public List<ExportItem> ExportItemList = new List<ExportItem>();
            public bool doExport = false;
        }
    }
}